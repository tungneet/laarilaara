"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";
import { useActingProfile } from "@/lib/profiles";

const STATUS_COPY: Record<string, { title: string; body: string; cta?: { href: string; label: string } }> = {
  draft: {
    title: "Your profile is a draft",
    body: "Complete the remaining sections and submit it for review to start appearing in discovery.",
    cta: { href: "/app/profile", label: "Continue editing" },
  },
  pending_review: {
    title: "Profile submitted",
    body: "Your profile has been submitted. Publish it to go live and start receiving interests.",
    cta: { href: "/app/profile", label: "Open profile" },
  },
  published: {
    title: "Your profile is live",
    body: "You're visible in discovery. Browse today's recommendations or fine-tune your preferences.",
    cta: { href: "/app/discover", label: "Browse matches" },
  },
  paused: {
    title: "Your profile is paused",
    body: "You're hidden from discovery while paused. Resume any time from your profile page.",
    cta: { href: "/app/profile", label: "Open profile" },
  },
};

export default function AppHome() {
  const { account } = useAuth();
  const { profiles, actingProfile, loading } = useActingProfile();

  if (loading) {
    return <p className="text-sm text-ink-soft">Loading your profiles…</p>;
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[28px] font-bold tracking-tight">
          Welcome{account ? `, ${account.display_name || account.email?.split("@")[0] || "back"}` : ""}
        </h1>
        <p className="mt-1 text-sm text-ink-soft">
          Manage your family&apos;s profiles and introductions from one place.
        </p>
      </header>

      {profiles.length === 0 ? (
        <section className="glass rounded-[26px] p-8 text-center">
          <h2 className="font-display text-xl font-semibold">
            Start by creating a profile
          </h2>
          <p className="mx-auto mt-2 mb-6 max-w-md text-sm leading-relaxed text-ink-soft">
            A profile can be for yourself, or for a family member you&apos;re
            helping — you stay in control either way.
          </p>
          <Link
            href="/app/onboarding"
            className="bg-gradient-brand inline-block rounded-full px-7 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
          >
            Create a profile
          </Link>
        </section>
      ) : (
        <>
          {actingProfile && (
            <section className="glass rounded-[26px] p-7">
              {(() => {
                const copy = STATUS_COPY[actingProfile.status] ?? {
                  title: `Profile status: ${actingProfile.status}`,
                  body: "",
                };
                return (
                  <>
                    <div className="mb-1.5 flex items-center gap-2.5">
                      <h2 className="font-display text-lg font-semibold">{copy.title}</h2>
                      <span className="rounded-full bg-primary-soft px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase">
                        {actingProfile.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="max-w-xl text-sm leading-relaxed text-ink-soft">{copy.body}</p>
                    {copy.cta && (
                      <Link
                        href={copy.cta.href}
                        className="bg-gradient-brand mt-5 inline-block rounded-full px-6 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
                      >
                        {copy.cta.label}
                      </Link>
                    )}
                  </>
                );
              })()}
            </section>
          )}

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              { href: "/app/discover", title: "Discover", body: "Search and browse compatible profiles." },
              { href: "/app/interests", title: "Interests", body: "See who's interested and respond." },
              { href: "/app/messages", title: "Messages", body: "Chat with your accepted matches." },
            ].map((card) => (
              <Link
                key={card.href}
                href={card.href}
                className="glass rounded-card p-5 transition-all duration-200 hover:-translate-y-1 hover:border-primary"
              >
                <h3 className="font-display text-[15.5px] font-semibold">{card.title}</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">{card.body}</p>
              </Link>
            ))}
          </section>

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold">Your profiles</h2>
              <Link
                href="/app/onboarding"
                className="glass rounded-full px-4 py-2 text-[12.5px] font-semibold transition-transform hover:-translate-y-px"
              >
                + New profile
              </Link>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {profiles.map((p) => (
                <div key={p.id} className="glass flex items-center justify-between rounded-card p-4">
                  <div>
                    <div className="text-[14.5px] font-semibold">
                      {p.relationship === "self"
                        ? "Managed by the candidate"
                        : "Managed by family"}
                      {p.is_primary && (
                        <span className="ml-2 text-[10.5px] font-semibold tracking-wide text-ink-soft uppercase">
                          primary manager
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 text-xs text-ink-soft">
                      Status: {p.status.replace("_", " ")} · v{p.version}
                    </div>
                  </div>
                  <Link
                    href="/app/profile"
                    className="rounded-full bg-primary-soft px-4 py-1.5 text-[12.5px] font-semibold"
                  >
                    Open
                  </Link>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
