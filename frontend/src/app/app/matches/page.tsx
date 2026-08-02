"use client";

/** Matches (Block 7, §8): list with chat links, end-match flow, and
 *  post-match feedback / outcome forms on ended matches. */

import Link from "next/link";
import { useState } from "react";

import { authErrorMessage } from "@/lib/auth";
import {
  useEndMatch,
  useMatchFeedback,
  useMatchOutcome,
  useMatches,
  type Match,
  type MatchOutcome,
} from "@/lib/matches";
import { useActingProfile } from "@/lib/profiles";

const OUTCOMES: { value: MatchOutcome; label: string }[] = [
  { value: "engaged", label: "Engaged 💍" },
  { value: "married", label: "Married 🎉" },
  { value: "ended_amicably", label: "Parted ways amicably" },
  { value: "other", label: "Other" },
];

function StarPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          onClick={() => onChange(n)}
          className={`cursor-pointer text-[20px] transition-transform hover:-translate-y-0.5 ${
            n <= value ? "" : "opacity-30"
          }`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function MatchCard({ match, actingId }: { match: Match; actingId: string }) {
  const endMatch = useEndMatch(actingId);
  const feedback = useMatchFeedback(actingId);
  const outcome = useMatchOutcome(actingId);

  const [confirmingEnd, setConfirmingEnd] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [selOutcome, setSelOutcome] = useState<MatchOutcome | "">("");
  const [consent, setConsent] = useState(false);
  const [outcomeSent, setOutcomeSent] = useState(false);

  const otherProfileId =
    match.profile_a_id === actingId ? match.profile_b_id : match.profile_a_id;
  const error = endMatch.error ?? feedback.error ?? outcome.error;

  return (
    <li className="glass rounded-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${
                match.status === "active" ? "bg-gradient-brand text-on-primary" : "bg-white/10"
              }`}
            >
              {match.status}
            </span>
            <span className="text-[12px] text-ink-soft">
              Matched {new Date(match.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/app/profiles/${otherProfileId}`}
            className="rounded-full border border-glass-line px-4 py-1.5 text-[12.5px] font-semibold transition-colors hover:border-primary"
          >
            View profile
          </Link>
          {match.status === "active" && match.conversation_id && (
            <Link
              href={`/app/messages?conversation=${match.conversation_id}`}
              className="bg-gradient-brand rounded-full px-4 py-1.5 text-[12.5px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110"
            >
              Open chat
            </Link>
          )}
          {match.status === "active" && (
            <button
              type="button"
              onClick={() => setConfirmingEnd((c) => !c)}
              className="cursor-pointer rounded-full border border-glass-line px-4 py-1.5 text-[12.5px] font-semibold text-ink-soft transition-colors hover:border-accent hover:text-ink"
            >
              End match
            </button>
          )}
        </div>
      </div>

      {error != null && (
        <p role="alert" className="mt-3 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
          {authErrorMessage(error)}
        </p>
      )}

      {confirmingEnd && match.status === "active" && (
        <div className="mt-4 rounded-xl border border-accent/40 bg-accent-soft px-4 py-3">
          <p className="mb-3 text-[12.5px] leading-relaxed">
            Ending closes the conversation for both families. This can&apos;t be
            undone. Continue?
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={endMatch.isPending}
              onClick={() => endMatch.mutate(match.id)}
              className="cursor-pointer rounded-full bg-accent px-4 py-1.5 text-[12.5px] font-bold text-on-primary disabled:opacity-60"
            >
              {endMatch.isPending ? "Ending…" : "Yes, end match"}
            </button>
            <button
              type="button"
              onClick={() => setConfirmingEnd(false)}
              className="cursor-pointer rounded-full border border-glass-line px-4 py-1.5 text-[12.5px] font-semibold"
            >
              Keep match
            </button>
          </div>
        </div>
      )}

      {match.status === "ended" && (
        <div className="mt-5 grid grid-cols-1 gap-4 border-t border-glass-line pt-5 sm:grid-cols-2">
          <div>
            <h3 className="mb-2 font-display text-[13.5px] font-semibold">
              How was this introduction?
            </h3>
            {feedbackSent ? (
              <p className="rounded-xl bg-primary-soft px-3.5 py-2.5 text-[12.5px]">
                Thanks — your feedback improves future matches.
              </p>
            ) : (
              <>
                <StarPicker value={rating} onChange={setRating} />
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  maxLength={2000}
                  placeholder="Optional comment…"
                  className="mt-2 mb-2 min-h-[54px] w-full resize-y rounded-xl border border-glass-line bg-white/5 px-3 py-2 text-[12.5px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-primary"
                />
                <button
                  type="button"
                  disabled={rating === 0 || feedback.isPending}
                  onClick={() =>
                    feedback.mutate(
                      { matchId: match.id, rating, comment },
                      { onSuccess: () => setFeedbackSent(true) },
                    )
                  }
                  className="cursor-pointer rounded-full bg-primary-soft px-4 py-1.5 text-[12.5px] font-semibold disabled:opacity-50"
                >
                  {feedback.isPending ? "Sending…" : "Send feedback"}
                </button>
              </>
            )}
          </div>

          <div>
            <h3 className="mb-2 font-display text-[13.5px] font-semibold">
              Share the outcome (optional)
            </h3>
            {outcomeSent ? (
              <p className="rounded-xl bg-primary-soft px-3.5 py-2.5 text-[12.5px]">
                Recorded — congratulations from LaariLaara! 🎊
              </p>
            ) : (
              <>
                <div className="mb-2 flex flex-wrap gap-1.5">
                  {OUTCOMES.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      aria-pressed={selOutcome === o.value}
                      onClick={() => setSelOutcome(o.value)}
                      className={`cursor-pointer rounded-full px-3 py-1.5 text-[12px] transition-colors ${
                        selOutcome === o.value
                          ? "bg-primary font-semibold text-on-primary"
                          : "border border-glass-line font-medium text-ink-soft hover:border-primary"
                      }`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
                <label className="mb-2 flex items-start gap-2 text-[12px] leading-relaxed text-ink-soft">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    className="mt-0.5 size-3.5 accent-(--primary)"
                  />
                  I consent to LaariLaara recording this outcome for community
                  success statistics.
                </label>
                <button
                  type="button"
                  disabled={!selOutcome || !consent || outcome.isPending}
                  onClick={() =>
                    outcome.mutate(
                      { matchId: match.id, outcome: selOutcome as MatchOutcome },
                      { onSuccess: () => setOutcomeSent(true) },
                    )
                  }
                  className="cursor-pointer rounded-full bg-primary-soft px-4 py-1.5 text-[12.5px] font-semibold disabled:opacity-50"
                >
                  {outcome.isPending ? "Recording…" : "Record outcome"}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

export default function MatchesPage() {
  const { actingProfile, loading } = useActingProfile();
  const matches = useMatches(actingProfile?.id);

  if (loading) return <p className="text-sm text-ink-soft">Loading…</p>;

  if (!actingProfile) {
    return (
      <div className="glass rounded-[26px] p-10 text-center">
        <h1 className="font-display text-[22px] font-bold">Create a profile first</h1>
        <p className="mx-auto mt-2 mb-6 max-w-md text-sm text-ink-soft">
          Matches appear once a profile has accepted interests.
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

  const items = matches.data?.items ?? [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[26px] font-bold tracking-tight">Matches</h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          Accepted introductions — chat, meet, and let us know how it goes.
        </p>
      </header>

      {matches.isLoading ? (
        <p className="text-sm text-ink-soft">Loading matches…</p>
      ) : items.length === 0 ? (
        <div className="glass rounded-[26px] p-10 text-center">
          <h2 className="font-display text-lg font-semibold">No matches yet</h2>
          <p className="mx-auto mt-2 mb-5 max-w-md text-sm leading-relaxed text-ink-soft">
            When an interest is accepted — by either side — the match appears
            here with its conversation.
          </p>
          <Link
            href="/app/interests"
            className="bg-gradient-brand inline-block rounded-full px-6 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
          >
            Review interests
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((match) => (
            <MatchCard key={match.id} match={match} actingId={actingProfile.id} />
          ))}
        </ul>
      )}
    </div>
  );
}
