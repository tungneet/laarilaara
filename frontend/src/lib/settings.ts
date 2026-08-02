"use client";

/** Hooks for Block 11 (Settings): account, sessions, contacts, password
 *  reset, and data requests — all account-scoped (no acting_profile_id). */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Account } from "@/lib/auth";

export function useUpdateLocale() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (locale: string) => api.patch<Account>("/v1/me", { locale }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export interface SessionSummary {
  id: string;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: () => api.get<SessionSummary[]>("/v1/me/sessions"),
  });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => api.delete<void>(`/v1/me/sessions/${sessionId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

// ---------------------------------------------------------------------------
// Contacts
// ---------------------------------------------------------------------------

export type ContactType = "email" | "phone";

export interface Contact {
  id: string;
  type: ContactType;
  masked_value: string;
  verified: boolean;
  created_at: string;
}

export function useContacts() {
  return useQuery({
    queryKey: ["contacts"],
    queryFn: () => api.get<Contact[]>("/v1/me/contacts"),
  });
}

export function useAddContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ type, value }: { type: ContactType; value: string }) =>
      api.post<Contact>("/v1/me/contacts", { type, value }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts"] }),
  });
}

export function useVerifyContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId, code }: { contactId: string; code: string }) =>
      api.post<Contact>(`/v1/me/contacts/${contactId}/verify`, { code }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts"] }),
  });
}

export function useRemoveContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contactId: string) => api.delete<void>(`/v1/me/contacts/${contactId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts"] }),
  });
}

// ---------------------------------------------------------------------------
// Password
// ---------------------------------------------------------------------------

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (email: string) => api.post<void>("/v1/auth/password/forgot", { email }),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: ({
      challengeId,
      code,
      newPassword,
    }: {
      challengeId: string;
      code: string;
      newPassword: string;
    }) =>
      api.post<void>("/v1/auth/password/reset", {
        challenge_id: challengeId,
        code,
        new_password: newPassword,
      }),
  });
}

// ---------------------------------------------------------------------------
// Data requests — no list endpoint exists server-side, so submitted request
// ids are tracked in localStorage per account and re-fetched by id.
// ---------------------------------------------------------------------------

export type DataRequestType = "export" | "correction" | "deletion";

export interface DataRequest {
  id: string;
  type: string;
  status: string;
  details: string | null;
  created_at: string;
  completed_at: string | null;
}

function trackedRequestIds(accountId: string): string[] {
  try {
    const raw = localStorage.getItem(`ll-data-requests:${accountId}`);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function trackRequestId(accountId: string, id: string) {
  try {
    const next = [id, ...trackedRequestIds(accountId).filter((existing) => existing !== id)];
    localStorage.setItem(`ll-data-requests:${accountId}`, JSON.stringify(next));
  } catch {
    /* private mode */
  }
}

export function useDataRequests(accountId: string | undefined) {
  return useQuery({
    queryKey: ["data-requests", accountId],
    queryFn: async () => {
      const ids = trackedRequestIds(accountId!);
      const results = await Promise.all(
        ids.map((id) =>
          api.get<DataRequest>(`/v1/me/data-requests/${id}`).catch(() => null),
        ),
      );
      return results.filter((item): item is DataRequest => item !== null);
    },
    enabled: !!accountId,
  });
}

export function useCreateDataRequest(accountId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ type, details }: { type: DataRequestType; details?: string }) =>
      api.post<DataRequest>("/v1/me/data-requests", { type, details: details || undefined }),
    onSuccess: (created) => {
      if (accountId) trackRequestId(accountId, created.id);
      queryClient.invalidateQueries({ queryKey: ["data-requests", accountId] });
    },
  });
}
