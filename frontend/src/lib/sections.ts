"use client";

/** Shared data hooks for the profile editor (catalog §5 sections). */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";

export function useSection<T>(profileId: string | null | undefined, path: string) {
  return useQuery({
    queryKey: ["section", profileId, path],
    queryFn: () => api.get<T>(`/v1/profiles/${profileId}${path}`),
    enabled: !!profileId,
  });
}

export interface CompletionView {
  profile_id: string;
  score: number;
  missing_sections: string[];
}

export function useCompletion(profileId: string | null | undefined) {
  return useQuery({
    queryKey: ["completion", profileId],
    queryFn: () => api.get<CompletionView>(`/v1/profiles/${profileId}/completion`),
    enabled: !!profileId,
  });
}

/** Mutation for saving a section; invalidates the section + completion and
 *  briefly reports `saved` for a "Saved ✓" indicator. */
export function useSectionSave(
  profileId: string | null | undefined,
  path: string,
  method: "patch" | "put" = "patch",
) {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);

  const mutation = useMutation({
    mutationFn: (body: unknown) =>
      method === "put"
        ? api.put(`/v1/profiles/${profileId}${path}`, body)
        : api.patch(`/v1/profiles/${profileId}${path}`, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["section", profileId] });
      await queryClient.invalidateQueries({ queryKey: ["completion", profileId] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  return { ...mutation, saved };
}

/** FormData → JSON body, skipping empty strings (partial-update semantics). */
export function formBody(data: FormData): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const [key, value] of data.entries()) {
    if (typeof value === "string" && value.trim() !== "") body[key] = value.trim();
  }
  return body;
}

/** "" | "true" | "false" select value → boolean | undefined. */
export function triBool(value: FormDataEntryValue | null): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}
