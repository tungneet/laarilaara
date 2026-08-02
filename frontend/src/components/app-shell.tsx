"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";
import { useActingProfile } from "@/lib/profiles";

const TABS = [
  { href: "/app", label: "Home" },
  { href: "/app/discover", label: "Discover" },
  { href: "/app/interests", label: "Interests" },
  { href: "/app/matches", label: "Matches" },
  { href: "/app/messages", label: "Messages" },
  { href: "/app/notifications", label: "Notifications" },
  { href: "/app/billing", label: "Billing" },
  { href: "/app/settings", label: "Settings" },
] as const;

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  pending_review: "In review",
  published: "Live",
  paused: "Paused",
  deleting: "Deleting",
};

function ProfileSwitcher() {
  const { profiles, actingProfile, setActingProfileId } = useActingProfile();

  if (profiles.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="acting-profile" className="text-xs text-ink-soft">
        Acting as
      </label>
      <select
        id="acting-profile"
        value={actingProfile?.id ?? ""}
        onChange={(e) => setActingProfileId(e.target.value)}
        className="glass cursor-pointer rounded-full px-3 py-2 text-[13px] font-medium text-ink outline-none [&>option]:bg-slate-800"
      >
        {profiles.map((p) => (
          <option key={p.id} value={p.id}>
            {p.relationship === "self" ? "Self-managed" : "Family-managed"} ·{" "}
            {STATUS_LABEL[p.status] ?? p.status}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Guarded shell for everything under /app. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { account, loading, signOut } = useAuth();

  useEffect(() => {
    if (!loading && !account) router.replace("/signin");
  }, [loading, account, router]);

  if (loading || !account) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-ink-soft">
        Loading…
      </div>
    );
  }

  return (
    <div className="relative z-10 mx-auto w-full max-w-[1180px] flex-1 px-5 sm:px-10">
      <nav className="flex items-center justify-between gap-3 py-5">
        <Link href="/app" className="font-display text-[22px] font-bold tracking-tight">
          <span className="brand-laari">Laari</span><span className="brand-laara">Laara</span>
        </Link>
        <div className="flex items-center gap-2.5">
          <ProfileSwitcher />
          <button
            type="button"
            onClick={async () => {
              await signOut();
              router.push("/");
            }}
            className="glass cursor-pointer rounded-full px-4 py-2 text-[13px] font-semibold transition-transform duration-150 hover:-translate-y-px"
          >
            Sign out
          </button>
        </div>
      </nav>

      <div className="glass mb-7 flex gap-1 overflow-x-auto rounded-full p-1.5">
        {TABS.map((tab) => {
          const active =
            tab.href === "/app" ? pathname === "/app" : pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`rounded-full px-4 py-2 text-[13.5px] whitespace-nowrap transition-colors ${
                active
                  ? "bg-primary font-semibold text-on-primary"
                  : "font-medium text-ink-soft hover:text-ink"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>

      <main className="pb-16">{children}</main>
    </div>
  );
}
