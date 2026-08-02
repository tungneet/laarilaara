"use client";

/** Hooks for matches (§8): list, end, feedback, outcome. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

const acting = (id: string) => `acting_profile_id=${encodeURIComponent(id)}`;

export type MatchOutcome = "engaged" | "married" | "ended_amicably" | "other";

export interface Match {
  id: string;
  interest_id: string;
  profile_a_id: string;
  profile_b_id: string;
  status: "active" | "ended";
  conversation_id: string | null;
  created_at: string;
  ended_at: string | null;
}

export function useMatches(actingProfileId: string | undefined) {
  return useQuery({
    queryKey: ["matches", actingProfileId],
    queryFn: () =>
      api.get<{ items: Match[] }>(`/v1/matches?${acting(actingProfileId!)}`),
    enabled: !!actingProfileId,
  });
}

export function useEndMatch(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (matchId: string) =>
      api.post<Match>(`/v1/matches/${matchId}/end?${acting(actingProfileId!)}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["matches", actingProfileId] }),
  });
}

export function useMatchFeedback(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: ({
      matchId,
      rating,
      comment,
    }: {
      matchId: string;
      rating: number;
      comment?: string;
    }) =>
      api.post(`/v1/matches/${matchId}/feedback?${acting(actingProfileId!)}`, {
        rating,
        comment: comment || undefined,
      }),
  });
}

export function useMatchOutcome(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: ({ matchId, outcome }: { matchId: string; outcome: MatchOutcome }) =>
      api.post(`/v1/matches/${matchId}/outcomes?${acting(actingProfileId!)}`, {
        outcome,
        consent: true, // the UI checkbox gates submission client-side
      }),
  });
}
