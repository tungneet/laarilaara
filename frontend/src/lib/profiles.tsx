"use client";

/**
 * Acting-profile context.
 *
 * An account can manage several profiles (self, children, siblings…). Most
 * backend endpoints take an `acting_profile_id` — this context owns which of
 * "my profiles" is currently active, persisted per-account in localStorage.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export interface MyProfile {
  id: string;
  relationship: "self" | "other";
  status: "draft" | "pending_review" | "published" | "paused" | "deleting";
  version: number;
  locale: string;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  published_at: string | null;
  paused_at: string | null;
  my_role: string;
  my_permissions: string[];
  is_primary: boolean;
}

interface MyProfilesResponse {
  items: MyProfile[];
}

interface ActingProfileContextValue {
  /** All profiles the signed-in account manages (empty while signed out). */
  profiles: MyProfile[];
  /** True while the list is loading for a signed-in account. */
  loading: boolean;
  /** The currently selected profile, if any. */
  actingProfile: MyProfile | null;
  setActingProfileId: (id: string) => void;
  /** Re-fetch the profile list (after create/submit/publish). */
  refresh: () => Promise<void>;
}

const ActingProfileContext = createContext<ActingProfileContextValue | null>(null);

const storageKey = (accountId: string) => `ll-acting-profile:${accountId}`;

export function ActingProfileProvider({ children }: { children: React.ReactNode }) {
  const { account } = useAuth();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["my-profiles", account?.id],
    queryFn: () => api.get<MyProfilesResponse>("/v1/me/profiles"),
    enabled: !!account,
  });

  const profiles = useMemo(
    () => (account ? (data?.items ?? []) : []),
    [account, data],
  );

  // Restore / default the selection whenever the list changes. This must stay
  // an effect (not render-time state adjustment) because it reads
  // localStorage, which is an external system and cannot run during render.
  useEffect(() => {
    if (!account || profiles.length === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedId(null);
      return;
    }
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(storageKey(account.id));
    } catch {
      /* private mode */
    }
    const valid = profiles.find((p) => p.id === stored) ?? profiles[0];
    setSelectedId(valid.id);
  }, [account, profiles]);

  const setActingProfileId = useCallback(
    (id: string) => {
      setSelectedId(id);
      if (account) {
        try {
          localStorage.setItem(storageKey(account.id), id);
        } catch {
          /* private mode */
        }
      }
    },
    [account],
  );

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["my-profiles"] });
  }, [queryClient]);

  const value = useMemo<ActingProfileContextValue>(
    () => ({
      profiles,
      loading: !!account && isLoading,
      actingProfile: profiles.find((p) => p.id === selectedId) ?? null,
      setActingProfileId,
      refresh,
    }),
    [profiles, account, isLoading, selectedId, setActingProfileId, refresh],
  );

  return (
    <ActingProfileContext.Provider value={value}>
      {children}
    </ActingProfileContext.Provider>
  );
}

export function useActingProfile(): ActingProfileContextValue {
  const ctx = useContext(ActingProfileContext);
  if (!ctx) {
    throw new Error("useActingProfile must be used within <ActingProfileProvider>");
  }
  return ctx;
}
