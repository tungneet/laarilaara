"use client";

/** Discovery (Block 4): recommendations feed + filtered search (§7). */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Field, FormError, SelectField } from "@/components/auth-form";
import { CandidateCard } from "@/components/candidate-card";
import { ChipSelect } from "@/components/chip-select";
import { authErrorMessage } from "@/lib/auth";
import {
  fetchRecommendations,
  searchProfiles,
  useShortlist,
  useShortlistToggle,
  type CandidateSummary,
  type SearchFilters,
} from "@/lib/discovery";
import { useActingProfile } from "@/lib/profiles";
import { useCommunities } from "@/lib/reference";

type Mode = "recommendations" | "search";

export default function DiscoverPage() {
  const { actingProfile, loading } = useActingProfile();
  const communities = useCommunities();
  const shortlist = useShortlist(actingProfile?.id);
  const shortlistToggle = useShortlistToggle(actingProfile?.id);

  const [mode, setMode] = useState<Mode>("recommendations");
  const [items, setItems] = useState<CandidateSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [selCommunities, setSelCommunities] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (
      currentMode: Mode,
      currentFilters: SearchFilters,
      nextCursor: string | null,
      append: boolean,
    ) => {
      if (!actingProfile) return;
      setBusy(true);
      setError(null);
      try {
        const page =
          currentMode === "recommendations"
            ? await fetchRecommendations(actingProfile.id, nextCursor)
            : await searchProfiles(actingProfile.id, currentFilters, nextCursor);
        setItems((prev) => (append ? [...prev, ...page.items] : page.items));
        setCursor(page.next_cursor);
      } catch (err) {
        setError(authErrorMessage(err));
      } finally {
        setBusy(false);
      }
    },
    [actingProfile],
  );

  // Initial + acting-profile-change load of recommendations. Must stay an
  // effect: it triggers a network fetch, which cannot run during render.
  useEffect(() => {
    if (actingProfile) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMode("recommendations");
      load("recommendations", {}, null, false);
    }
  }, [actingProfile, load]);

  function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const next: SearchFilters = {};
    const gender = String(data.get("gender") ?? "");
    if (gender) next.gender = gender;
    const minAge = String(data.get("min_age") ?? "");
    if (minAge) next.min_age = Number(minAge);
    const maxAge = String(data.get("max_age") ?? "");
    if (maxAge) next.max_age = Number(maxAge);
    if (selCommunities.length > 0) next.communities = selCommunities;
    setFilters(next);
    setMode("search");
    load("search", next, null, false);
  }

  if (loading) return <p className="text-sm text-ink-soft">Loading…</p>;

  if (!actingProfile) {
    return (
      <div className="glass rounded-[26px] p-10 text-center">
        <h1 className="font-display text-[22px] font-bold">Create a profile first</h1>
        <p className="mx-auto mt-2 mb-6 max-w-md text-sm text-ink-soft">
          Discovery works on behalf of a profile — create one to start browsing.
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

  const shortlistedIds = new Set((shortlist.data ?? []).map((s) => s.target_profile_id));

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-[26px] font-bold tracking-tight">Discover</h1>
          <p className="mt-0.5 text-sm text-ink-soft">
            {mode === "recommendations"
              ? "Today's recommendations for your profile."
              : "Search results."}
          </p>
        </div>
        {mode === "search" && (
          <button
            type="button"
            onClick={() => {
              setMode("recommendations");
              load("recommendations", {}, null, false);
            }}
            className="glass cursor-pointer rounded-full px-4 py-2 text-[13px] font-semibold transition-transform hover:-translate-y-px"
          >
            ← Back to recommendations
          </button>
        )}
      </header>

      <details className="glass rounded-[26px] p-6 open:pb-7">
        <summary className="cursor-pointer font-display text-[15.5px] font-semibold">
          Search with filters
        </summary>
        <form onSubmit={onSearch} noValidate className="mt-5">
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-3">
            <SelectField label="Gender" name="gender" defaultValue="">
              <option value="">Any</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </SelectField>
            <Field label="Age from" name="min_age" type="number" min={18} max={120} placeholder="25" />
            <Field label="Age to" name="max_age" type="number" min={18} max={120} placeholder="35" />
          </div>
          <ChipSelect
            label="Communities"
            options={(communities.data ?? []).map((c) => ({ value: c.id, label: c.label }))}
            selected={selCommunities}
            onChange={setSelCommunities}
            hint="Leave empty to include all communities."
          />
          <button
            type="submit"
            disabled={busy}
            className="bg-gradient-brand cursor-pointer rounded-full px-7 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:opacity-60"
          >
            {busy ? "Searching…" : "Search"}
          </button>
        </form>
      </details>

      <FormError message={error} />

      {items.length === 0 && !busy ? (
        <div className="glass rounded-[26px] p-10 text-center">
          <h2 className="font-display text-lg font-semibold">No profiles found</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-soft">
            {mode === "search"
              ? "Try widening your filters — or check back soon as new profiles publish."
              : "No published profiles to recommend yet — invite the family to publish theirs!"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((candidate) => (
            <CandidateCard
              key={candidate.profile_id}
              candidate={candidate}
              shortlisted={shortlistedIds.has(candidate.profile_id)}
              shortlistBusy={shortlistToggle.isPending}
              onToggleShortlist={() =>
                shortlistToggle.mutate({
                  targetId: candidate.profile_id,
                  shortlisted: shortlistedIds.has(candidate.profile_id),
                })
              }
            />
          ))}
        </div>
      )}

      {cursor && (
        <div className="text-center">
          <button
            type="button"
            disabled={busy}
            onClick={() => load(mode, filters, cursor, true)}
            className="glass cursor-pointer rounded-full px-7 py-2.5 text-sm font-semibold transition-transform hover:-translate-y-px disabled:opacity-60"
          >
            {busy ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
