"use client";

/** Data hooks for discovery (§7) + shortlist quick actions. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface CandidateSummary {
  profile_id: string;
  age: number | null;
  gender: string | null;
  height_cm: number | null;
  marital_status: string | null;
  headline: string | null;
}

export interface CandidateDetail extends CandidateSummary {
  bio: string | null;
}

export interface DiscoveryPage {
  items: CandidateSummary[];
  next_cursor: string | null;
}

export interface SearchFilters {
  gender?: string;
  min_age?: number;
  max_age?: number;
  communities?: string[];
}

export function fetchRecommendations(
  actingProfileId: string,
  cursor?: string | null,
): Promise<DiscoveryPage> {
  const params = new URLSearchParams({ acting_profile_id: actingProfileId });
  if (cursor) params.set("cursor", cursor);
  return api.get<DiscoveryPage>(`/v1/discovery/recommendations?${params}`);
}

export function searchProfiles(
  actingProfileId: string,
  filters: SearchFilters,
  cursor?: string | null,
): Promise<DiscoveryPage> {
  return api.post<DiscoveryPage>(
    `/v1/discovery/search?acting_profile_id=${encodeURIComponent(actingProfileId)}`,
    { filters, cursor: cursor ?? undefined },
  );
}

export function useCandidate(actingProfileId: string | undefined, profileId: string) {
  return useQuery({
    queryKey: ["candidate", actingProfileId, profileId],
    queryFn: () =>
      api.get<CandidateDetail>(
        `/v1/discovery/profiles/${profileId}?acting_profile_id=${encodeURIComponent(actingProfileId!)}`,
      ),
    enabled: !!actingProfileId,
  });
}

export function recordView(actingProfileId: string, targetProfileId: string) {
  return api.post(
    `/v1/discovery/views?acting_profile_id=${encodeURIComponent(actingProfileId)}`,
    { target_profile_id: targetProfileId },
  );
}

// --- shortlist ---

interface ShortlistItem {
  target_profile_id: string;
  note: string | null;
}

export function useShortlist(actingProfileId: string | undefined) {
  return useQuery({
    queryKey: ["shortlist", actingProfileId],
    queryFn: () =>
      api.get<ShortlistItem[]>(
        `/v1/shortlist?acting_profile_id=${encodeURIComponent(actingProfileId!)}`,
      ),
    enabled: !!actingProfileId,
  });
}

export function useShortlistToggle(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ targetId, shortlisted }: { targetId: string; shortlisted: boolean }) =>
      shortlisted
        ? api.delete(
            `/v1/shortlist/${targetId}?acting_profile_id=${encodeURIComponent(actingProfileId!)}`,
          )
        : api.put(
            `/v1/shortlist/${targetId}?acting_profile_id=${encodeURIComponent(actingProfileId!)}`,
            { note: null },
          ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["shortlist", actingProfileId] }),
  });
}
