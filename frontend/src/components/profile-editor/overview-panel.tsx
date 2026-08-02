"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SectionCard } from "@/components/profile-editor/section-card";
import { api } from "@/lib/api";
import { useActingProfile, type MyProfile } from "@/lib/profiles";
import { useCompletion } from "@/lib/sections";

const SECTION_LABELS: Record<string, string> = {
  personal_details: "Personal details",
  narratives: "About",
  lifestyle: "Lifestyle",
  visibility: "Privacy",
  communities: "Community",
  family: "Family",
  education: "Education",
  employment: "Career",
  preferences: "Preferences",
  media: "Photos",
};

function LifecycleButton({
  label,
  onClick,
  busy,
  primary,
}: {
  label: string;
  onClick: () => void;
  busy: boolean;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className={`cursor-pointer rounded-full px-6 py-2.5 text-sm font-semibold transition-all duration-150 hover:-translate-y-px disabled:cursor-default disabled:opacity-60 ${
        primary
          ? "bg-gradient-brand text-on-primary hover:brightness-110"
          : "glass"
      }`}
    >
      {busy ? "Working…" : label}
    </button>
  );
}

export function OverviewPanel({ profile }: { profile: MyProfile }) {
  const queryClient = useQueryClient();
  const { refresh } = useActingProfile();
  const completion = useCompletion(profile.id);
  const [error, setError] = useState<unknown>(null);

  const lifecycle = useMutation({
    mutationFn: (action: "submit" | "publish" | "pause" | "resume") =>
      api.post(`/v1/profiles/${profile.id}/${action}`),
    onSuccess: async () => {
      setError(null);
      await refresh();
      await queryClient.invalidateQueries({ queryKey: ["completion", profile.id] });
    },
    onError: setError,
  });

  const score = completion.data?.score ?? 0;
  const missing = completion.data?.missing_sections ?? [];

  return (
    <div className="space-y-5">
      <SectionCard title="Status" error={error}>
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-primary-soft px-3.5 py-1.5 text-[12px] font-semibold tracking-wide uppercase">
            {profile.status.replace("_", " ")}
          </span>
          <span className="rounded-full border border-glass-line px-3.5 py-1.5 text-[12px] font-medium text-ink-soft">
            {profile.relationship === "self"
              ? "Managed by the candidate"
              : "Managed by family"}
          </span>
          <span className="text-[13px] text-ink-soft">version {profile.version}</span>
        </div>
        <div className="flex flex-wrap gap-3">
          {profile.status === "draft" && (
            <LifecycleButton
              label="Submit for review"
              onClick={() => lifecycle.mutate("submit")}
              busy={lifecycle.isPending}
              primary
            />
          )}
          {profile.status === "pending_review" && (
            <LifecycleButton
              label="Publish"
              onClick={() => lifecycle.mutate("publish")}
              busy={lifecycle.isPending}
              primary
            />
          )}
          {profile.status === "published" && (
            <LifecycleButton
              label="Pause profile"
              onClick={() => lifecycle.mutate("pause")}
              busy={lifecycle.isPending}
            />
          )}
          {profile.status === "paused" && (
            <LifecycleButton
              label="Resume profile"
              onClick={() => lifecycle.mutate("resume")}
              busy={lifecycle.isPending}
              primary
            />
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="Profile completion"
        description="Complete profiles get significantly better discovery placement."
      >
        <div className="mb-3 flex items-center gap-4">
          <div
            className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/10"
            role="progressbar"
            aria-valuenow={score}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="bg-gradient-brand h-full rounded-full transition-all duration-500"
              style={{ width: `${score}%` }}
            />
          </div>
          <span className="font-display text-lg font-bold">{score}%</span>
        </div>
        {missing.length > 0 && (
          <p className="text-[13px] leading-relaxed text-ink-soft">
            Still missing:{" "}
            {missing.map((s) => SECTION_LABELS[s] ?? s.replaceAll("_", " ")).join(", ")}
          </p>
        )}
      </SectionCard>
    </div>
  );
}
