"use client";

/** Hooks for the interests inbox/outbox (§8): list by direction +
 *  accept / decline / withdraw state transitions. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Interest } from "@/lib/safety";

const acting = (id: string) => `acting_profile_id=${encodeURIComponent(id)}`;

export type InterestDirection = "incoming" | "outgoing";

export interface InterestFull extends Interest {
  decline_reason: string | null;
  created_at: string;
  updated_at: string;
}

export function useInterests(
  actingProfileId: string | undefined,
  direction: InterestDirection,
) {
  return useQuery({
    queryKey: ["interests", actingProfileId, direction],
    queryFn: () =>
      api.get<{ items: InterestFull[] }>(
        `/v1/interests?${acting(actingProfileId!)}&direction=${direction}`,
      ),
    enabled: !!actingProfileId,
  });
}

export type InterestAction = "accept" | "decline" | "withdraw";

export function useInterestAction(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      interestId,
      action,
      reason,
    }: {
      interestId: string;
      action: InterestAction;
      reason?: string;
    }) =>
      api.post<InterestFull>(
        `/v1/interests/${interestId}/${action}?${acting(actingProfileId!)}`,
        action === "decline" ? { reason: reason || undefined } : undefined,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["interests", actingProfileId] });
      // Accepting creates a match — refresh anything match-related too.
      queryClient.invalidateQueries({ queryKey: ["matches", actingProfileId] });
    },
  });
}
