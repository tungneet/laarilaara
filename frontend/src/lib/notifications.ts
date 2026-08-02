"use client";

/** Hooks for the in-app notification center (§12): inbox list + mark
 *  read/read-all + delivery preferences. All resources here are
 *  ACCOUNT-scoped (no acting_profile_id), unlike most other domains. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface Notification {
  id: string;
  category: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
}

export interface NotificationPreferences {
  categories: Record<string, string[]>;
  updated_at: string | null;
}

export const NOTIFICATION_CATEGORIES = [
  "match",
  "message",
  "interest",
  "moderation",
  "system",
] as const;

export const NOTIFICATION_CHANNELS = ["in_app", "email", "push"] as const;

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      api.get<{ items: Notification[]; next_cursor: string | null }>(
        "/v1/notifications?limit=50",
      ),
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      api.post<Notification>(`/v1/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/v1/notifications/read-all", {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: ["notification-preferences"],
    queryFn: () => api.get<NotificationPreferences>("/v1/notification-preferences"),
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (categories: Record<string, string[]>) =>
      api.put<NotificationPreferences>("/v1/notification-preferences", { categories }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-preferences"] });
    },
  });
}
