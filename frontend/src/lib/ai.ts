"use client";

/**
 * Hooks for the AI-assisted domain endpoints (catalog §10 / Block 14).
 *
 * Every generation endpoint is synchronous end-to-end (the backend runs the
 * central AI engine inline and the artifact is already `succeeded`/`failed`
 * by the time the POST response comes back), so these are plain mutations —
 * no polling needed. Results are read from `result` on success.
 *
 * NOTE: `apply_artifact` on the backend only *validates* (profile version +
 * artifact readiness) — it does not merge the draft into profile fields.
 * These hooks don't call it; instead, the UI copies the generated text
 * straight into the relevant form field for the user to review and save
 * through the normal section-save flow.
 */

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";

const acting = (id: string) => `acting_profile_id=${encodeURIComponent(id)}`;

export interface AiArtifact<TResult> {
  id: string;
  kind: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled" | "expired";
  subject: { type: string; id: string; version: number | null };
  result: TResult | null;
  error: { message?: string } | null;
  created_at: string;
  completed_at: string | null;
}

// --- Profile-scoped ---

export function useCreateBioDraft(profileId: string | undefined) {
  return useMutation({
    mutationFn: (tone: string | undefined) =>
      api.post<AiArtifact<{ bio: string }>>(`/v1/profiles/${profileId}/ai/bio-drafts`, {
        tone: tone || undefined,
      }),
  });
}

export function useCreateExtractionDraft(profileId: string | undefined) {
  return useMutation({
    mutationFn: (text: string) =>
      api.post<AiArtifact<{ fields: { headline?: string }; note?: string }>>(
        `/v1/profiles/${profileId}/ai/extraction-drafts`,
        { text },
      ),
  });
}

export function useCreateQualityAnalysis(profileId: string | undefined) {
  return useMutation({
    mutationFn: () =>
      api.post<AiArtifact<{ score: number | string; suggestions: string[] }>>(
        `/v1/profiles/${profileId}/ai/quality-analyses`,
        {},
      ),
  });
}

// --- Discovery-scoped ---

export function useCreateSearchDraft(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: (query: string) =>
      api.post<AiArtifact<{ filters: Record<string, unknown>; note?: string }>>(
        `/v1/discovery/search-drafts?${acting(actingProfileId!)}`,
        { query },
      ),
  });
}

// --- Compatibility-scoped ---

export function useCreateCompatibilityExplanation(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: (analysisId: string) =>
      api.post<AiArtifact<{ summary: string }>>(
        `/v1/compatibility-analyses/${analysisId}/explanation?${acting(actingProfileId!)}`,
        {},
      ),
  });
}

// --- Conversation-scoped ---

export function useCreateAssistantDraft(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: ({
      conversationId,
      intent,
      tone,
      locale,
    }: {
      conversationId: string;
      intent: string;
      tone?: string;
      locale?: string;
    }) =>
      api.post<AiArtifact<{ draft: string }>>(
        `/v1/conversations/${conversationId}/assistant-drafts?${acting(actingProfileId!)}`,
        { intent, tone: tone || undefined, locale: locale || undefined },
      ),
  });
}

export function useCreateTranslationDraft(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: ({
      conversationId,
      targetLocale,
      text,
    }: {
      conversationId: string;
      targetLocale: string;
      text: string;
    }) =>
      api.post<AiArtifact<{ translated_text: string; target_locale: string | null; note?: string }>>(
        `/v1/conversations/${conversationId}/translation-drafts?${acting(actingProfileId!)}`,
        { target_locale: targetLocale, text },
      ),
  });
}

export function useCreateToneCheck(actingProfileId: string | undefined) {
  return useMutation({
    mutationFn: ({ conversationId, text }: { conversationId: string; text: string }) =>
      api.post<AiArtifact<{ tone: string; suggestions: string[] }>>(
        `/v1/conversations/${conversationId}/tone-checks?${acting(actingProfileId!)}`,
        { text },
      ),
  });
}
