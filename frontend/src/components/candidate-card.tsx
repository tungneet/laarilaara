"use client";

import Link from "next/link";

import type { CandidateSummary } from "@/lib/discovery";

const label = (value: string) =>
  value.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

function initials(candidate: CandidateSummary): string {
  if (candidate.headline) {
    const words = candidate.headline.split(/\s+/).slice(0, 2);
    return words.map((w) => w[0]?.toUpperCase() ?? "").join("");
  }
  return candidate.profile_id.slice(0, 2).toUpperCase();
}

export function CandidateCard({
  candidate,
  shortlisted,
  onToggleShortlist,
  shortlistBusy,
}: {
  candidate: CandidateSummary;
  shortlisted: boolean;
  onToggleShortlist: () => void;
  shortlistBusy: boolean;
}) {
  const facts = [
    candidate.age != null ? `${candidate.age}` : null,
    candidate.height_cm != null ? `${candidate.height_cm} cm` : null,
    candidate.marital_status ? label(candidate.marital_status) : null,
  ].filter(Boolean);

  return (
    <div className="overflow-hidden rounded-card border border-glass-line bg-white/5 transition-all duration-200 hover:-translate-y-1 hover:border-primary">
      <div className="relative grid h-[130px] place-items-center bg-[radial-gradient(circle_at_30%_20%,var(--primary-soft),transparent_60%),radial-gradient(circle_at_75%_80%,var(--accent-soft),transparent_55%)] font-display text-4xl font-bold text-white/20">
        {initials(candidate)}
        <button
          type="button"
          disabled={shortlistBusy}
          onClick={onToggleShortlist}
          aria-pressed={shortlisted}
          title={shortlisted ? "Remove from shortlist" : "Add to shortlist"}
          className={`absolute top-3 right-3 grid size-9 cursor-pointer place-items-center rounded-full border text-[15px] backdrop-blur transition-all ${
            shortlisted
              ? "border-accent bg-accent-soft"
              : "border-glass-line bg-black/25 hover:border-accent"
          }`}
        >
          {shortlisted ? "★" : "☆"}
        </button>
      </div>
      <div className="p-4">
        <div className="line-clamp-2 min-h-[42px] font-display text-[15px] leading-snug font-semibold">
          {candidate.headline ?? "Profile"}
        </div>
        <div className="mt-1 mb-3 text-[12.5px] text-ink-soft">
          {facts.length > 0 ? facts.join(" · ") : "Details on profile"}
        </div>
        <Link
          href={`/app/profiles/${candidate.profile_id}`}
          className="bg-gradient-brand block cursor-pointer rounded-full py-2 text-center text-[13px] font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
        >
          View profile
        </Link>
      </div>
    </div>
  );
}
