"use client";

import { authErrorMessage } from "@/lib/auth";

/** Card wrapper for one editable section, with save state feedback. */
export function SectionCard({
  title,
  description,
  saved,
  error,
  children,
}: {
  title: string;
  description?: string;
  saved?: boolean;
  error?: unknown;
  children: React.ReactNode;
}) {
  return (
    <section className="glass rounded-[26px] p-7">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold">{title}</h2>
          {description && (
            <p className="mt-0.5 text-[13px] text-ink-soft">{description}</p>
          )}
        </div>
        {saved && (
          <span
            role="status"
            className="rounded-full bg-primary-soft px-3 py-1 text-[12px] font-semibold"
          >
            Saved ✓
          </span>
        )}
      </div>
      {error != null && (
        <p
          role="alert"
          className="mb-4 rounded-xl border border-accent/40 bg-accent-soft px-4 py-2.5 text-[13.5px]"
        >
          {authErrorMessage(error)}
        </p>
      )}
      {children}
    </section>
  );
}

export function SaveButton({ busy, label = "Save changes" }: { busy: boolean; label?: string }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="bg-gradient-brand mt-1 cursor-pointer rounded-full px-6 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:cursor-default disabled:opacity-60 disabled:hover:translate-y-0"
    >
      {busy ? "Saving…" : label}
    </button>
  );
}
