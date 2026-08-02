"use client";

/**
 * Applies the personalized bride/groom theme automatically.
 *
 * Pre-login and while gender is unknown, the app stays on the neutral
 * (common) theme. As soon as gender is known — from the account (captured at
 * signup) or, once set, the acting profile's personal details — the matching
 * variant is applied: female → bride, male → groom, other/unset → neutral.
 * The profile's own gender (once saved) takes precedence over the account's.
 */

import { useEffect } from "react";

import { useAuth } from "@/lib/auth";
import { useActingProfile } from "@/lib/profiles";
import { useSection } from "@/lib/sections";

function applyTheme(theme: "bride" | "groom" | null) {
  if (theme) {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("ll-theme", theme);
    } catch {
      /* private mode */
    }
  } else {
    delete document.documentElement.dataset.theme;
    try {
      localStorage.removeItem("ll-theme");
    } catch {
      /* private mode */
    }
  }
}

export function ThemeController() {
  const { account } = useAuth();
  const { actingProfile } = useActingProfile();
  const details = useSection<{ gender: string | null }>(
    actingProfile?.id,
    "/personal-details",
  );

  useEffect(() => {
    if (!account) {
      applyTheme(null);
      return;
    }
    if (actingProfile && !details.isSuccess) return; // keep whatever is applied until we know
    const gender = (actingProfile && details.data?.gender) || account.gender;
    applyTheme(gender === "female" ? "bride" : gender === "male" ? "groom" : null);
  }, [account, actingProfile, details.isSuccess, details.data?.gender]);

  return null;
}
