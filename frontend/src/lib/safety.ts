"use client";

/** Hooks for compatibility (§8), interests-send (§8), and safety controls
 *  (§7 hide, §11 block/report) used on the candidate detail page. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

const acting = (id: string) => `acting_profile_id=${encodeURIComponent(id)}`;

// --- compatibility ---

export interface CompatibilityAnalysis {
  id: string;
  acting_profile_id: string;
  target_profile_id: string;
  score: number;
  factors: Record<string, number>;
}

/** POST is idempotent per (acting,target) pair — safe to treat as a read. */
export function useCompatibility(
  actingProfileId: string | undefined,
  targetProfileId: string,
) {
  return useQuery({
    queryKey: ["compatibility", actingProfileId, targetProfileId],
    queryFn: () =>
      api.post<CompatibilityAnalysis>(
        `/v1/compatibility-analyses?${acting(actingProfileId!)}`,
        { target_profile_id: targetProfileId },
      ),
    enabled: !!actingProfileId,
    staleTime: 5 * 60_000,
  });
}

// --- interests (send + outgoing lookup; the full inbox is Block 6) ---

export interface Interest {
  id: string;
  from_profile_id: string;
  to_profile_id: string;
  message: string | null;
  status: "pending" | "accepted" | "declined" | "withdrawn";
  match_id: string | null;
}

export function useOutgoingInterests(actingProfileId: string | undefined) {
  return useQuery({
    queryKey: ["interests", actingProfileId, "outgoing"],
    queryFn: () =>
      api.get<{ items: Interest[] }>(
        `/v1/interests?${acting(actingProfileId!)}&direction=outgoing`,
      ),
    enabled: !!actingProfileId,
  });
}

export function useSendInterest(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ targetId, message }: { targetId: string; message?: string }) =>
      api.post<Interest>(`/v1/interests?${acting(actingProfileId!)}`, {
        target_profile_id: targetId,
        message: message || undefined,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["interests", actingProfileId] }),
  });
}

// --- safety: hide / block / report ---

export function useHideProfile(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: (targetId: string) =>
      api.put(`/v1/hidden-profiles/${targetId}?${acting(actingProfileId!)}`),
  });
}

export function useBlocks(actingProfileId: string | undefined) {
  return useQuery({
    queryKey: ["blocks", actingProfileId],
    queryFn: () =>
      api.get<{ target_profile_id: string }[]>(`/v1/blocks?${acting(actingProfileId!)}`),
    enabled: !!actingProfileId,
  });
}

export function useBlockProfile(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetId: string) =>
      api.put(`/v1/blocks/${targetId}?${acting(actingProfileId!)}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["blocks", actingProfileId] }),
  });
}

export interface ReportInput {
  subject_type: "profile" | "message" | "conversation" | "media";
  subject_id: string;
  reason: string;
  details?: string;
}

export function useSendReport(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: (input: ReportInput) =>
      api.post(`/v1/reports?${acting(actingProfileId!)}`, input),
  });
}
