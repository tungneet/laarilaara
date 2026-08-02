"use client";

/**
 * Candidate detail (Block 5): discovery projection + compatibility score,
 * express interest, shortlist, and safety controls (hide / block / report).
 * Records a profile view on open (§7, idempotent per day server-side).
 */

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { SelectField, TextAreaField } from "@/components/auth-form";
import { ApiError } from "@/lib/api";
import { useCreateCompatibilityExplanation } from "@/lib/ai";
import { authErrorMessage } from "@/lib/auth";
import { recordView, useCandidate, useShortlist, useShortlistToggle } from "@/lib/discovery";
import { useActingProfile } from "@/lib/profiles";
import {
  useBlockProfile,
  useCompatibility,
  useHideProfile,
  useOutgoingInterests,
  useSendInterest,
  useSendReport,
} from "@/lib/safety";

const label = (value: string) =>
  value.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

const REPORT_REASONS = [
  "fake_profile",
  "inappropriate_content",
  "harassment",
  "scam_or_fraud",
  "married_or_unavailable",
  "other",
];

function CompatibilityCard({
  actingId,
  targetId,
}: {
  actingId: string;
  targetId: string;
}) {
  const compatibility = useCompatibility(actingId, targetId);
  const explain = useCreateCompatibilityExplanation(actingId);

  if (compatibility.isError) return null; // non-essential — never block the page
  const data = compatibility.data;

  return (
    <div className="glass rounded-[26px] p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-[15px] font-semibold">Compatibility</h2>
        {data && (
          <span className="bg-gradient-brand rounded-full px-3 py-1 font-display text-[14px] font-bold text-on-primary">
            {data.score}%
          </span>
        )}
      </div>
      {!data ? (
        <p className="text-[13px] text-ink-soft">Calculating…</p>
      ) : (
        <div className="space-y-2.5">
          {Object.entries(data.factors).map(([name, value]) => (
            <div key={name}>
              <div className="mb-1 flex justify-between text-[12px] text-ink-soft">
                <span>{label(name)}</span>
                <span>{value}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="bg-gradient-brand h-full rounded-full"
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          ))}
          <p className="pt-1 text-[11.5px] leading-relaxed text-ink-soft">
            Based on age, community overlap, and lifestyle. Improves as both
            profiles add more detail.
          </p>
          <button
            type="button"
            disabled={explain.isPending}
            onClick={() => explain.mutate(data.id)}
            className="cursor-pointer rounded-full border border-glass-line px-4 py-1.5 text-[12px] font-semibold text-ink-soft transition-colors hover:border-primary hover:text-ink disabled:opacity-50"
          >
            {explain.isPending ? "Thinking…" : "✨ Explain this in words"}
          </button>
          {explain.error != null && (
            <p className="text-[12px] text-accent">{authErrorMessage(explain.error)}</p>
          )}
          {explain.data?.result?.summary && (
            <p className="glass rounded-xl p-3.5 text-[13px] leading-relaxed">
              {explain.data.result.summary}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function InterestCard({
  actingId,
  targetId,
}: {
  actingId: string;
  targetId: string;
}) {
  const outgoing = useOutgoingInterests(actingId);
  const send = useSendInterest(actingId);
  const [message, setMessage] = useState("");

  const existing = (outgoing.data?.items ?? []).find(
    (i) => i.to_profile_id === targetId && i.status !== "withdrawn",
  );

  if (existing) {
    return (
      <div className="glass rounded-[26px] p-6">
        <h2 className="mb-2 font-display text-[15px] font-semibold">Interest</h2>
        <p className="text-[13.5px] leading-relaxed text-ink-soft">
          {existing.status === "pending" && "Interest sent — waiting for their response."}
          {existing.status === "accepted" && "Interest accepted — you're matched! 🎉"}
          {existing.status === "declined" && "They passed this time."}
        </p>
        <Link
          href={existing.status === "accepted" ? "/app/matches" : "/app/interests"}
          className="mt-3 inline-block rounded-full bg-primary-soft px-4 py-1.5 text-[12.5px] font-semibold"
        >
          {existing.status === "accepted" ? "Go to matches" : "Manage in Interests"}
        </Link>
      </div>
    );
  }

  return (
    <div className="glass rounded-[26px] p-6">
      <h2 className="mb-2 font-display text-[15px] font-semibold">Express interest</h2>
      {send.isError && (
        <p role="alert" className="mb-3 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
          {authErrorMessage(send.error)}
        </p>
      )}
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        maxLength={1000}
        placeholder="Add a short note (optional)…"
        className="mb-3 min-h-[70px] w-full resize-y rounded-xl border border-glass-line bg-white/5 px-3.5 py-2.5 text-[13.5px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-primary"
      />
      <button
        type="button"
        disabled={send.isPending}
        onClick={() => send.mutate({ targetId, message })}
        className="bg-gradient-brand w-full cursor-pointer rounded-full py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:opacity-60"
      >
        {send.isPending ? "Sending…" : "Send interest"}
      </button>
    </div>
  );
}

function SafetyCard({
  actingId,
  targetId,
}: {
  actingId: string;
  targetId: string;
}) {
  const router = useRouter();
  const hide = useHideProfile(actingId);
  const block = useBlockProfile(actingId);
  const report = useSendReport(actingId);
  const [confirming, setConfirming] = useState<"block" | null>(null);
  const [reporting, setReporting] = useState(false);
  const [reportSent, setReportSent] = useState(false);

  function onReport(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    report.mutate(
      {
        subject_type: "profile",
        subject_id: targetId,
        reason: String(data.get("reason")),
        details: String(data.get("details") ?? "").trim() || undefined,
      },
      { onSuccess: () => setReportSent(true) },
    );
  }

  return (
    <div className="glass rounded-[26px] p-6">
      <h2 className="mb-3 font-display text-[15px] font-semibold">Not interested?</h2>
      {(hide.isError || block.isError || report.isError) && (
        <p role="alert" className="mb-3 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
          {authErrorMessage(hide.error ?? block.error ?? report.error)}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={hide.isPending}
          onClick={() =>
            hide.mutate(targetId, { onSuccess: () => router.push("/app/discover") })
          }
          className="glass cursor-pointer rounded-full px-4 py-2 text-[12.5px] font-semibold transition-transform hover:-translate-y-px disabled:opacity-60"
        >
          {hide.isPending ? "Hiding…" : "Hide from my discovery"}
        </button>
        <button
          type="button"
          onClick={() => setConfirming("block")}
          className="glass cursor-pointer rounded-full px-4 py-2 text-[12.5px] font-semibold transition-transform hover:-translate-y-px"
        >
          Block
        </button>
        <button
          type="button"
          onClick={() => setReporting((r) => !r)}
          className="glass cursor-pointer rounded-full px-4 py-2 text-[12.5px] font-semibold transition-transform hover:-translate-y-px"
        >
          Report
        </button>
      </div>

      {confirming === "block" && (
        <div className="mt-4 rounded-xl border border-accent/40 bg-accent-soft px-4 py-3">
          <p className="mb-3 text-[12.5px] leading-relaxed">
            Blocking hides you from each other everywhere and cannot be seen by
            them. Continue?
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={block.isPending}
              onClick={() =>
                block.mutate(targetId, { onSuccess: () => router.push("/app/discover") })
              }
              className="cursor-pointer rounded-full bg-accent px-4 py-1.5 text-[12.5px] font-bold text-on-primary disabled:opacity-60"
            >
              {block.isPending ? "Blocking…" : "Yes, block"}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(null)}
              className="cursor-pointer rounded-full border border-glass-line px-4 py-1.5 text-[12.5px] font-semibold"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {reporting && !reportSent && (
        <form onSubmit={onReport} className="mt-4" noValidate>
          <SelectField label="Reason" name="reason" required defaultValue="">
            <option value="" disabled>
              Select a reason…
            </option>
            {REPORT_REASONS.map((r) => (
              <option key={r} value={r}>
                {label(r)}
              </option>
            ))}
          </SelectField>
          <TextAreaField
            label="Details (optional)"
            name="details"
            maxLength={2000}
            placeholder="Anything that helps our review team…"
          />
          <button
            type="submit"
            disabled={report.isPending}
            className="cursor-pointer rounded-full bg-primary-soft px-5 py-2 text-[12.5px] font-semibold disabled:opacity-60"
          >
            {report.isPending ? "Submitting…" : "Submit report"}
          </button>
        </form>
      )}
      {reportSent && (
        <p className="mt-4 rounded-xl bg-primary-soft px-4 py-3 text-[12.5px] leading-relaxed">
          Report received — our safety team will review it. Thank you for
          keeping the community safe.
        </p>
      )}
    </div>
  );
}

export default function CandidatePage() {
  const params = useParams<{ id: string }>();
  const profileId = params.id;
  const { actingProfile, loading } = useActingProfile();
  const candidate = useCandidate(actingProfile?.id, profileId);
  const shortlist = useShortlist(actingProfile?.id);
  const shortlistToggle = useShortlistToggle(actingProfile?.id);
  const viewRecorded = useRef(false);

  useEffect(() => {
    if (actingProfile && candidate.isSuccess && !viewRecorded.current) {
      viewRecorded.current = true;
      recordView(actingProfile.id, profileId).catch(() => {
        /* view logging must never break the page */
      });
    }
  }, [actingProfile, candidate.isSuccess, profileId]);

  if (loading || candidate.isLoading) {
    return <p className="text-sm text-ink-soft">Loading profile…</p>;
  }

  if (candidate.isError) {
    const notFound =
      candidate.error instanceof ApiError && candidate.error.status === 404;
    return (
      <div className="glass rounded-[26px] p-10 text-center">
        <h1 className="font-display text-[22px] font-bold">
          {notFound ? "Profile not available" : "Something went wrong"}
        </h1>
        <p className="mx-auto mt-2 mb-6 max-w-md text-sm text-ink-soft">
          {notFound
            ? "This profile may have been paused or is no longer published."
            : "Please try again in a moment."}
        </p>
        <Link
          href="/app/discover"
          className="glass inline-block rounded-full px-6 py-2.5 text-sm font-semibold transition-transform hover:-translate-y-px"
        >
          ← Back to discovery
        </Link>
      </div>
    );
  }

  // Covers the disabled-query window while the acting profile restores.
  if (!candidate.data || !actingProfile) {
    return <p className="text-sm text-ink-soft">Loading profile…</p>;
  }

  const data = candidate.data;
  const shortlisted = (shortlist.data ?? []).some(
    (s) => s.target_profile_id === profileId,
  );
  const facts = [
    data.age != null ? `${data.age} years` : null,
    data.height_cm != null ? `${data.height_cm} cm` : null,
    data.marital_status ? label(data.marital_status) : null,
    data.gender ? label(data.gender) : null,
  ].filter(Boolean);

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <Link
        href="/app/discover"
        className="inline-block text-[13px] font-medium text-ink-soft hover:text-ink"
      >
        ← Back to discovery
      </Link>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
        {/* main column */}
        <div className="glass h-fit overflow-hidden rounded-[26px]">
          <div className="grid h-[180px] place-items-center bg-[radial-gradient(circle_at_30%_20%,var(--primary-soft),transparent_60%),radial-gradient(circle_at_75%_80%,var(--accent-soft),transparent_55%)] font-display text-6xl font-bold text-white/20">
            {(data.headline ?? "P").slice(0, 1).toUpperCase()}
          </div>
          <div className="p-7">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="font-display text-[24px] leading-tight font-bold tracking-tight">
                  {data.headline ?? "Profile"}
                </h1>
                <p className="mt-1 text-[13.5px] text-ink-soft">{facts.join(" · ")}</p>
              </div>
              <button
                type="button"
                disabled={shortlistToggle.isPending}
                onClick={() =>
                  shortlistToggle.mutate({ targetId: profileId, shortlisted })
                }
                aria-pressed={shortlisted}
                className={`cursor-pointer rounded-full border px-5 py-2 text-[13px] font-semibold transition-all hover:-translate-y-px disabled:opacity-60 ${
                  shortlisted
                    ? "border-accent bg-accent-soft"
                    : "border-glass-line hover:border-accent"
                }`}
              >
                {shortlisted ? "★ Shortlisted" : "☆ Shortlist"}
              </button>
            </div>

            {data.bio && (
              <div className="mt-6">
                <h2 className="mb-2 font-display text-[15px] font-semibold">About</h2>
                <p className="text-[14.5px] leading-relaxed whitespace-pre-line text-ink-soft">
                  {data.bio}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* side column */}
        <div className="space-y-5">
          <CompatibilityCard actingId={actingProfile.id} targetId={profileId} />
          <InterestCard actingId={actingProfile.id} targetId={profileId} />
          <SafetyCard actingId={actingProfile.id} targetId={profileId} />
        </div>
      </div>
    </div>
  );
}
