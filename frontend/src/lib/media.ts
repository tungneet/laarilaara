"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type PhotoVisibility = "public" | "connections_only" | "managers_only";

export interface ProfileMedia {
  id: string;
  asset_id: string;
  is_primary: boolean;
  visibility: PhotoVisibility | null;
  caption: string | null;
  order: number | null;
  created_at: string;
  updated_at: string;
}

interface UploadTicket {
  id: string;
  upload_url: string;
}

interface MediaAsset {
  id: string;
  status: string;
  download_url: string | null;
}

export type UploadStage =
  | "Preparing photo…"
  | "Uploading photo…"
  | "Checking photo…"
  | "Adding to profile…";

async function sha256(file: File): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export function useProfileMedia(profileId: string | undefined) {
  return useQuery({
    queryKey: ["profile-media", profileId],
    queryFn: () => api.get<ProfileMedia[]>(`/v1/profiles/${profileId}/media`),
    enabled: !!profileId,
  });
}

export function useMediaAsset(assetId: string | undefined) {
  return useQuery({
    queryKey: ["media-asset", assetId],
    queryFn: () => api.get<MediaAsset>(`/v1/media/${assetId}`),
    enabled: !!assetId,
    staleTime: 4 * 60 * 1000,
  });
}

export function useUploadProfilePhoto(profileId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      caption,
      visibility,
      isPrimary,
      onStage,
    }: {
      file: File;
      caption: string;
      visibility: PhotoVisibility;
      isPrimary: boolean;
      onStage: (stage: UploadStage) => void;
    }) => {
      onStage("Preparing photo…");
      const checksum = await sha256(file);
      const ticket = await api.post<UploadTicket>("/v1/uploads", {
        purpose: "profile_photo",
        content_type: file.type,
        size_bytes: file.size,
        checksum,
      });

      onStage("Uploading photo…");
      const upload = await fetch(ticket.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type },
        body: file,
      });
      if (!upload.ok) {
        throw new Error(`Photo upload failed (${upload.status}).`);
      }

      onStage("Checking photo…");
      await api.post(`/v1/uploads/${ticket.id}/complete`);

      onStage("Adding to profile…");
      return api.post<ProfileMedia>(`/v1/profiles/${profileId}/media`, {
        asset_id: ticket.id,
        is_primary: isPrimary,
        visibility,
        caption: caption.trim() || null,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profile-media", profileId] });
      await queryClient.invalidateQueries({ queryKey: ["my-profiles"] });
    },
  });
}

export function useUpdateProfileMedia(profileId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ mediaId, updates }: { mediaId: string; updates: Partial<Pick<ProfileMedia, "caption" | "visibility" | "is_primary">> }) =>
      api.patch<ProfileMedia>(`/v1/profiles/${profileId}/media/${mediaId}`, updates),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["profile-media", profileId] }),
  });
}

export function useDeleteProfileMedia(profileId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ mediaId, assetId }: { mediaId: string; assetId: string }) => {
      await api.delete(`/v1/profiles/${profileId}/media/${mediaId}`);
      await api.delete(`/v1/media/${assetId}`);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["profile-media", profileId] });
      queryClient.invalidateQueries({ queryKey: ["my-profiles"] });
    },
  });
}