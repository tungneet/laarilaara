"use client";

/** Tabbed profile editor (Block 3) — every §5 section, completion, lifecycle. */

import Link from "next/link";
import { useState } from "react";

import { CommunityPanel } from "@/components/profile-editor/community-panel";
import { AiAssistPanel } from "@/components/profile-editor/ai-assist-panel";
import { FamilyPanel } from "@/components/profile-editor/family-panel";
import { OverviewPanel } from "@/components/profile-editor/overview-panel";
import { PhotosPanel } from "@/components/profile-editor/photos-panel";
import { PreferencesPanel } from "@/components/profile-editor/preferences-panel";
import { RecordsPanel } from "@/components/profile-editor/records-panel";
import {
  AboutPanel,
  BasicsPanel,
  LifestylePanel,
  PrivacyPanel,
} from "@/components/profile-editor/simple-panels";
import { useActingProfile } from "@/lib/profiles";

const TABS = [
  "Overview",
  "Basics",
  "Photos",
  "About",
  "AI Assist",
  "Lifestyle",
  "Community",
  "Family",
  "Education & Career",
  "Preferences",
  "Privacy",
] as const;

type Tab = (typeof TABS)[number];

export default function ProfileEditorPage() {
  const { actingProfile, loading } = useActingProfile();
  const [tab, setTab] = useState<Tab>("Overview");

  if (loading) {
    return <p className="text-sm text-ink-soft">Loading profile…</p>;
  }

  if (!actingProfile) {
    return (
      <div className="glass rounded-[26px] p-10 text-center">
        <h1 className="font-display text-[22px] font-bold">No profile yet</h1>
        <p className="mx-auto mt-2 mb-6 max-w-md text-sm text-ink-soft">
          Create a profile first — then manage every section from here.
        </p>
        <Link
          href="/app/onboarding"
          className="bg-gradient-brand inline-block rounded-full px-7 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
        >
          Create a profile
        </Link>
      </div>
    );
  }

  const profileId = actingProfile.id;

  return (
    <div>
      <h1 className="mb-5 font-display text-[26px] font-bold tracking-tight">
        My profile
      </h1>

      <div
        role="tablist"
        aria-label="Profile sections"
        className="mb-6 flex flex-wrap gap-1.5"
      >
        {TABS.map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`cursor-pointer rounded-full px-4 py-2 text-[13px] transition-colors ${
              tab === t
                ? "bg-primary font-semibold text-on-primary"
                : "border border-glass-line font-medium text-ink-soft hover:border-primary hover:text-ink"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && <OverviewPanel profile={actingProfile} />}
      {tab === "Basics" && <BasicsPanel profileId={profileId} />}
      {tab === "Photos" && <PhotosPanel profileId={profileId} />}
      {tab === "About" && <AboutPanel profileId={profileId} />}
      {tab === "AI Assist" && <AiAssistPanel profileId={profileId} />}
      {tab === "Lifestyle" && <LifestylePanel profileId={profileId} />}
      {tab === "Community" && <CommunityPanel profileId={profileId} />}
      {tab === "Family" && <FamilyPanel profileId={profileId} />}
      {tab === "Education & Career" && <RecordsPanel profileId={profileId} />}
      {tab === "Preferences" && <PreferencesPanel profileId={profileId} />}
      {tab === "Privacy" && <PrivacyPanel profileId={profileId} />}
    </div>
  );
}
