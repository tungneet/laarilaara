import Link from "next/link";

import { ProfileCard, type ProfileCardData } from "@/components/profile-card";
import { SiteNav } from "@/components/site-nav";

// Placeholder cards until discovery/recommendations are wired to the API.
const sampleProfiles: ProfileCardData[] = [
  {
    initials: "SK",
    name: "Simran K.",
    meta: "27 · Chandigarh · Software Engineer",
    identityTag: "An engineer who finds joy in farming",
    tags: ["Vegetarian", "Punjabi", "Masters"],
    score: 92,
    verified: true,
    photo: "/sample-profiles/simran.png",
  },
  {
    initials: "AS",
    name: "Arjun S.",
    meta: "29 · Toronto · Physician",
    identityTag: "A physician who brings people together through food",
    tags: ["Non-smoker", "Gursikh", "MD"],
    score: 88,
    verified: true,
    photo: "/sample-profiles/arjun.png",
  },
  {
    initials: "HG",
    name: "Harleen G.",
    meta: "26 · London · Architect",
    identityTag: "An architect who creates art after hours",
    tags: ["Amritdhari", "Vegetarian", "B.Arch"],
    score: 85,
    verified: true,
    photo: "/sample-profiles/harleen.png",
  },
];

export default function Home() {
  return (
    <div className="relative z-10 mx-auto w-full max-w-[1180px] flex-1 px-5 sm:px-10">
      <SiteNav />

      <section className="pt-16 pb-11 text-center sm:pt-[72px]">
        <div className="glass mb-6 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-[12.5px] text-ink-soft">
          <span className="inline-block size-[7px] rounded-full bg-accent" />
          Every profile identity-verified · Family-first by design
        </div>
        <h1 className="mx-auto max-w-[17ch] font-display text-[clamp(38px,5.2vw,64px)] leading-[1.06] font-bold tracking-[-1.5px]">
          Modern matchmaking, <span className="text-gradient">timeless values.</span>
        </h1>
        <p className="mx-auto mt-5 mb-8 max-w-[52ch] text-[16.5px] leading-relaxed text-ink-soft">
          A world-class matrimony experience for candidates and their parents —
          intelligent compatibility, respectful introductions, and privacy you
          control.
        </p>
        <div className="flex justify-center gap-3.5">
          <Link
            href="/signup"
            className="bg-gradient-brand rounded-full px-6 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
          >
            Get started free
          </Link>
          <Link
            href="/#how-it-works"
            className="glass rounded-full px-6 py-2.5 text-sm font-semibold transition-transform duration-150 hover:-translate-y-px"
          >
            See how it works
          </Link>
        </div>
      </section>

      <section className="glass mx-auto mt-16 mb-10 rounded-[26px] p-6 shadow-[0_40px_80px_-40px_rgba(0,0,0,0.6)] backdrop-blur-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="font-display text-[19px] font-semibold tracking-tight">
            Today&apos;s recommendations
          </h2>
          <div className="hidden gap-2 sm:flex">
            <button
              type="button"
              className="cursor-pointer rounded-full border border-primary bg-primary-soft px-3.5 py-1.5 text-[12.5px] font-medium"
            >
              Best match
            </button>
            <button
              type="button"
              className="cursor-pointer rounded-full border border-glass-line px-3.5 py-1.5 text-[12.5px] font-medium text-ink-soft"
            >
              Nearby
            </button>
            <button
              type="button"
              className="cursor-pointer rounded-full border border-glass-line px-3.5 py-1.5 text-[12.5px] font-medium text-ink-soft"
            >
              Recently joined
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {sampleProfiles.map((profile) => (
            <ProfileCard key={profile.name} profile={profile} />
          ))}
        </div>
      </section>

      <footer className="py-7 text-center text-[12.5px] text-ink-soft">
        LaariLaara · Trusted matrimony, reimagined
      </footer>
    </div>
  );
}
