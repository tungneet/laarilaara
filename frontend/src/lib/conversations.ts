"use client";

/** Messaging (§9): conversations, messages, and the realtime WebSocket. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { api, API_BASE_URL } from "@/lib/api";

const acting = (id: string) => `acting_profile_id=${encodeURIComponent(id)}`;

export interface Conversation {
  id: string;
  match_id: string;
  profile_a_id: string;
  profile_b_id: string;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
  muted: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_profile_id: string;
  client_message_id: string;
  body: string | null;
  status: "sent" | "edited" | "deleted";
  created_at: string;
  edited_at: string | null;
}

export function useConversations(actingProfileId: string | undefined) {
  return useQuery({
    queryKey: ["conversations", actingProfileId],
    queryFn: () =>
      api.get<{ items: Conversation[] }>(`/v1/conversations?${acting(actingProfileId!)}`),
    enabled: !!actingProfileId,
  });
}

export function useMessages(
  actingProfileId: string | undefined,
  conversationId: string | null,
) {
  return useQuery({
    queryKey: ["messages", actingProfileId, conversationId],
    queryFn: () =>
      api.get<{ items: Message[] }>(
        `/v1/conversations/${conversationId}/messages?${acting(actingProfileId!)}&limit=100`,
      ),
    enabled: !!actingProfileId && !!conversationId,
  });
}

export function useSendMessage(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, body }: { conversationId: string; body: string }) =>
      api.post<Message>(
        `/v1/conversations/${conversationId}/messages?${acting(actingProfileId!)}`,
        { client_message_id: crypto.randomUUID(), body },
      ),
    onSuccess: (_message, { conversationId }) => {
      queryClient.invalidateQueries({ queryKey: ["messages", actingProfileId, conversationId] });
      queryClient.invalidateQueries({ queryKey: ["conversations", actingProfileId] });
    },
  });
}

export function useEditMessage(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      messageId,
      body,
    }: {
      conversationId: string;
      messageId: string;
      body: string;
    }) =>
      api.patch<Message>(
        `/v1/conversations/${conversationId}/messages/${messageId}?${acting(actingProfileId!)}`,
        { body },
      ),
    onSuccess: (_m, { conversationId }) =>
      queryClient.invalidateQueries({ queryKey: ["messages", actingProfileId, conversationId] }),
  });
}

export function useDeleteMessage(actingProfileId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, messageId }: { conversationId: string; messageId: string }) =>
      api.delete(
        `/v1/conversations/${conversationId}/messages/${messageId}?${acting(actingProfileId!)}`,
      ),
    onSuccess: (_r, { conversationId }) =>
      queryClient.invalidateQueries({ queryKey: ["messages", actingProfileId, conversationId] }),
  });
}

export function markRead(
  actingProfileId: string,
  conversationId: string,
  messageId: string,
) {
  return api.post(`/v1/conversations/${conversationId}/read?${acting(actingProfileId)}`, {
    message_id: messageId,
  });
}

// --- realtime WebSocket ---

export interface RealtimeEvent {
  eventId: string;
  type:
    | "message.created"
    | "message.updated"
    | "message.deleted"
    | "conversation.read"
    | "typing.changed";
  occurredAt: string;
  resourceId: string;
  payload: Record<string, unknown>;
}

/**
 * Maintains a realtime WebSocket for the acting profile. Mints a short-lived
 * token per (re)connect, retries with backoff, and cleans up on unmount.
 * Returns a typing-signal sender.
 */
export function useRealtime(
  actingProfileId: string | undefined,
  onEvent: (event: RealtimeEvent) => void,
) {
  const socketRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!actingProfileId) return;
    let disposed = false;
    let attempts = 0;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    async function connect() {
      try {
        const { token } = await api.post<{ token: string }>("/v1/realtime-tokens", {
          profile_id: actingProfileId,
        });
        if (disposed) return;
        const wsBase = API_BASE_URL.replace(/^http/, "ws");
        const ws = new WebSocket(`${wsBase}/v1/realtime?token=${encodeURIComponent(token)}`);
        socketRef.current = ws;

        ws.onopen = () => {
          attempts = 0;
        };
        ws.onmessage = (msg) => {
          try {
            onEventRef.current(JSON.parse(msg.data) as RealtimeEvent);
          } catch {
            /* ignore malformed frames */
          }
        };
        ws.onclose = () => {
          socketRef.current = null;
          if (!disposed && attempts < 5) {
            attempts += 1;
            retryTimer = setTimeout(connect, Math.min(1000 * 2 ** attempts, 15000));
          }
        };
      } catch {
        if (!disposed && attempts < 5) {
          attempts += 1;
          retryTimer = setTimeout(connect, Math.min(1000 * 2 ** attempts, 15000));
        }
      }
    }

    connect();
    return () => {
      disposed = true;
      clearTimeout(retryTimer);
      socketRef.current?.close(1000, "navigate");
      socketRef.current = null;
    };
  }, [actingProfileId]);

  return {
    sendTyping(conversationId: string, typing: boolean) {
      const ws = socketRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            action: typing ? "typing.start" : "typing.stop",
            conversationId,
          }),
        );
      }
    },
  };
}
