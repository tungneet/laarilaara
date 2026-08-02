"use client";

/** Interests inbox/outbox (Block 6, §8): incoming & outgoing tabs with
 *  accept / decline (with optional reason) / withdraw transitions. */

import Link from "next/link";
import { useState } from "react";

import { authErrorMessage } from "@/lib/auth";
import {
  useInterestAction,
  useInterests,
  type InterestDirection,
  type InterestFull,
} from "@/lib/interests";
import { useActingProfile } from "@/lib/profiles";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-primary-soft",
  accepted: "bg-gradient-brand text-on-primary",
  declined: "bg-white/10",
  withdrawn: "bg-white/10",
};

function InterestRow({
  interest,
  direction,
  actingId,
}: {
  interest: InterestFull;
  direction: InterestDirection;
  actingId: string;
}) {
  const action = useInterestAction(actingId);
  const [declining, setDeclining] = useState(false);
  const [reason, setReason] = useState("");

  const otherProfileId =
    direction === "incoming" ? interest.from_profile_id : interest.to_profile_id;

  return (
    <li className="glass rounded-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${STATUS_BADGE[interest.status]}`}
            >
              {interest.status}
            </span>
            <span className="text-[12px] text-ink-soft">
              {new Date(interest.created_at).toLocaleDateString()}
            </span>
          </div>
          {interest.message && (
            <p className="mt-2.5 text-[14px] leading-relaxed text-ink-soft">
              “{interest.message}”
            </p>
          )}
          {interest.status === "declined" && interest.decline_reason && (
            <p className="mt-2 text-[12.5px] text-ink-soft">
              Reason: {interest.decline_reason}
            </p>
          )}
        </div>
        <Link
          href={`/app/profiles/${otherProfileId}`}
          className="shrink-0 rounded-full border border-glass-line px-4 py-1.5 text-[12.5px] font-semibold transition-colors hover:border-primary"
        >
          View profile
        </Link>
      </div>

      {action.isError && (
        <p role="alert" className="mt-3 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
          {authErrorMessage(action.error)}
        </p>
      )}

      {interest.status === "pending" && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {direction === "incoming" ? (
            <>
              <button
                type="button"
                disabled={action.isPending}
                onClick={() =>
                  action.mutate({ interestId: interest.id, action: "accept" })
                }
                className="bg-gradient-brand cursor-pointer rounded-full px-6 py-2 text-[13px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110 disabled:opacity-60"
              >
                {action.isPending ? "Working…" : "Accept"}
              </button>
              <button
                type="button"
                onClick={() => setDeclining((d) => !d)}
                className="glass cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold transition-transform hover:-translate-y-px"
              >
                Decline
              </button>
            </>
          ) : (
            <button
              type="button"
              disabled={action.isPending}
              onClick={() =>
                action.mutate({ interestId: interest.id, action: "withdraw" })
              }
              className="glass cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold transition-transform hover:-translate-y-px disabled:opacity-60"
            >
              {action.isPending ? "Working…" : "Withdraw"}
            </button>
          )}
        </div>
      )}

      {declining && interest.status === "pending" && (
        <div className="mt-3">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={1000}
            placeholder="Optional reason (shared with the sender)…"
            className="mb-2 w-full rounded-xl border border-glass-line bg-white/5 px-3.5 py-2 text-[13px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-primary"
          />
          <button
            type="button"
            disabled={action.isPending}
            onClick={() =>
              action.mutate({ interestId: interest.id, action: "decline", reason })
            }
            className="cursor-pointer rounded-full bg-accent-soft px-5 py-2 text-[12.5px] font-semibold disabled:opacity-60"
          >
            {action.isPending ? "Declining…" : "Confirm decline"}
          </button>
        </div>
      )}

      {interest.status === "accepted" && (
        <Link
          href="/app/matches"
          className="mt-4 inline-block rounded-full bg-primary-soft px-5 py-2 text-[12.5px] font-semibold"
        >
          Go to your match →
        </Link>
      )}
    </li>
  );
}

export default function InterestsPage() {
  const { actingProfile, loading } = useActingProfile();
  const [direction, setDirection] = useState<InterestDirection>("incoming");
  const interests = useInterests(actingProfile?.id, direction);

  if (loading) return <p className="text-sm text-ink-soft">Loading…</p>;

  if (!actingProfile) {
    return (
      <div className="glass rounded-[26px] p-10 text-center">
        <h1 className="font-display text-[22px] font-bold">Create a profile first</h1>
        <p className="mx-auto mt-2 mb-6 max-w-md text-sm text-ink-soft">
          Interests are sent and received on behalf of a profile.
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

  const items = interests.data?.items ?? [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[26px] font-bold tracking-tight">Interests</h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          Respond to who&apos;s interested, and track the interests you&apos;ve sent.
        </p>
      </header>

      <div role="tablist" aria-label="Interest direction" className="glass inline-flex gap-1 rounded-full p-1.5">
        {(["incoming", "outgoing"] as const).map((d) => (
          <button
            key={d}
            role="tab"
            aria-selected={direction === d}
            onClick={() => setDirection(d)}
            className={`cursor-pointer rounded-full px-5 py-2 text-[13.5px] transition-colors ${
              direction === d
                ? "bg-primary font-semibold text-on-primary"
                : "font-medium text-ink-soft hover:text-ink"
            }`}
          >
            {d === "incoming" ? "Received" : "Sent"}
          </button>
        ))}
      </div>

      {interests.isLoading ? (
        <p className="text-sm text-ink-soft">Loading interests…</p>
      ) : items.length === 0 ? (
        <div className="glass rounded-[26px] p-10 text-center">
          <h2 className="font-display text-lg font-semibold">
            {direction === "incoming" ? "No interests received yet" : "No interests sent yet"}
          </h2>
          <p className="mx-auto mt-2 mb-5 max-w-md text-sm leading-relaxed text-ink-soft">
            {direction === "incoming"
              ? "When someone expresses interest in your profile, it appears here."
              : "Browse discovery and express interest in profiles you like."}
          </p>
          <Link
            href="/app/discover"
            className="bg-gradient-brand inline-block rounded-full px-6 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
          >
            Browse profiles
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((interest) => (
            <InterestRow
              key={interest.id}
              interest={interest}
              direction={direction}
              actingId={actingProfile.id}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
