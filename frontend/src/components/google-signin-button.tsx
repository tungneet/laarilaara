"use client";

import { useEffect, useRef, useState } from "react";
import { authErrorMessage, useAuth } from "@/lib/auth";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: { theme: string; size: string; type: string },
          ) => void;
        };
      };
    };
  }
}

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
  if (existing) {
    return new Promise((resolve) => existing.addEventListener("load", () => resolve()));
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Identity Services"));
    document.head.appendChild(script);
  });
}

export function GoogleSignInButton({ onError }: { onError: (message: string) => void }) {
  const { loginWithGoogle } = useAuth();
  const containerRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !containerRef.current) return;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !window.google || !containerRef.current) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            setBusy(true);
            try {
              await loginWithGoogle(response.credential);
              window.location.href = "/app";
            } catch (err) {
              onError(authErrorMessage(err));
              setBusy(false);
            }
          },
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          theme: "outline",
          size: "large",
          type: "standard",
        });
      })
      .catch(() => onError("Couldn't load Google sign-in. Please try again."));

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!GOOGLE_CLIENT_ID) return null;

  return (
    <div className="mb-5">
      <style>{`
        #google-signin-button {
          display: flex !important;
          justify-content: center !important;
        }
        #google-signin-button > div {
          transform: scale(0.85);
          transform-origin: center;
        }
      `}</style>
      <div ref={containerRef} id="google-signin-button" className={busy ? "pointer-events-none opacity-60" : ""} />
      <div className="my-4 flex items-center gap-3 text-[12px] text-ink-soft">
        <div className="h-px flex-1 bg-glass-line" />
        <span>or</span>
        <div className="h-px flex-1 bg-glass-line" />
      </div>
    </div>
  );
}
