"use client";

/** Messaging (Block 8, §9): conversation list + chat thread with realtime
 *  message push, typing indicators, read marking, and edit/delete. */

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { MessageAiToolbar } from "@/components/message-ai-toolbar";
import { authErrorMessage } from "@/lib/auth";
import {
  markRead,
  useConversations,
  useDeleteMessage,
  useEditMessage,
  useMessages,
  useRealtime,
  useSendMessage,
  type Conversation,
  type RealtimeEvent,
} from "@/lib/conversations";
import { useActingProfile } from "@/lib/profiles";

function ConversationList({
  conversations,
  selectedId,
  onSelect,
}: {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (conversations.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-[13px] leading-relaxed text-ink-soft">
          No conversations yet — accept an interest to start one.
        </p>
        <Link
          href="/app/interests"
          className="mt-3 inline-block rounded-full bg-primary-soft px-4 py-1.5 text-[12.5px] font-semibold"
        >
          Review interests
        </Link>
      </div>
    );
  }

  return (
    <ul>
      {conversations.map((c) => (
        <li key={c.id}>
          <button
            type="button"
            onClick={() => onSelect(c.id)}
            className={`w-full cursor-pointer border-b border-glass-line px-5 py-4 text-left transition-colors last:border-b-0 ${
              selectedId === c.id ? "bg-primary-soft" : "hover:bg-white/5"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-display text-[13.5px] font-semibold">
                Conversation
              </span>
              {c.unread_count > 0 && (
                <span className="bg-gradient-brand grid size-5 place-items-center rounded-full text-[10.5px] font-bold text-on-primary">
                  {c.unread_count}
                </span>
              )}
            </div>
            <p className="mt-1 line-clamp-1 text-[12.5px] text-ink-soft">
              {c.last_message_preview ?? "Say hello 👋"}
            </p>
          </button>
        </li>
      ))}
    </ul>
  );
}

function MessageBubble({
  mine,
  body,
  status,
  time,
  onEdit,
  onDelete,
}: {
  mine: boolean;
  body: string | null;
  status: string;
  time: string;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  return (
    <div className={`group flex ${mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${
          mine ? "bg-primary-soft" : "border border-glass-line bg-white/5"
        }`}
      >
        {status === "deleted" ? (
          <p className="text-[13px] italic opacity-50">Message deleted</p>
        ) : (
          <p className="text-[14px] leading-relaxed whitespace-pre-line">{body}</p>
        )}
        <div className="mt-1 flex items-center gap-2 text-[10.5px] text-ink-soft">
          <span>
            {new Date(time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {status === "edited" && <span>· edited</span>}
          {mine && status !== "deleted" && (
            <span className="hidden gap-1.5 group-hover:flex">
              {onEdit && (
                <button type="button" onClick={onEdit} className="cursor-pointer underline">
                  edit
                </button>
              )}
              {onDelete && (
                <button type="button" onClick={onDelete} className="cursor-pointer underline">
                  delete
                </button>
              )}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function MessagesInner() {
  const { actingProfile, loading } = useActingProfile();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const conversations = useConversations(actingProfile?.id);
  const [selectedId, setSelectedId] = useState<string | null>(
    searchParams.get("conversation"),
  );
  const [autoSelectedFrom, setAutoSelectedFrom] = useState(conversations.data);
  const messages = useMessages(actingProfile?.id, selectedId);
  const send = useSendMessage(actingProfile?.id);
  const edit = useEditMessage(actingProfile?.id);
  const remove = useDeleteMessage(actingProfile?.id);

  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState<{ id: string; body: string } | null>(null);
  const [peerTyping, setPeerTyping] = useState(false);
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const lastTypingSent = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Realtime: refresh caches on message events; surface typing.
  const onEvent = useCallback(
    (event: RealtimeEvent) => {
      if (event.type === "typing.changed") {
        if (event.resourceId === selectedId) {
          setPeerTyping(Boolean(event.payload.typing));
          clearTimeout(typingTimeout.current);
          if (event.payload.typing) {
            typingTimeout.current = setTimeout(() => setPeerTyping(false), 5000);
          }
        }
        return;
      }
      queryClient.invalidateQueries({ queryKey: ["messages", actingProfile?.id, event.resourceId] });
      queryClient.invalidateQueries({ queryKey: ["conversations", actingProfile?.id] });
    },
    [queryClient, actingProfile?.id, selectedId],
  );
  const { sendTyping } = useRealtime(actingProfile?.id, onEvent);

  // Select first conversation by default, without an effect (React's
  // recommended pattern for adjusting state when new data arrives).
  if (
    conversations.data !== autoSelectedFrom &&
    !selectedId &&
    (conversations.data?.items.length ?? 0) > 0
  ) {
    setAutoSelectedFrom(conversations.data);
    setSelectedId(conversations.data!.items[0].id);
  }

  // Mark read (up to the newest message) when opening / when new messages arrive.
  useEffect(() => {
    const items = messages.data?.items ?? [];
    if (actingProfile && selectedId && items.length > 0) {
      const newest = items[items.length - 1];
      markRead(actingProfile.id, selectedId, newest.id)
        .then(() =>
          queryClient.invalidateQueries({ queryKey: ["conversations", actingProfile.id] }),
        )
        .catch(() => {});
    }
  }, [actingProfile, selectedId, messages.data, queryClient]);

  // Keep scrolled to the newest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data?.items.length, selectedId]);

  if (loading) return <p className="text-sm text-ink-soft">Loading…</p>;

  if (!actingProfile) {
    return (
      <div className="glass rounded-[26px] p-10 text-center">
        <h1 className="font-display text-[22px] font-bold">Create a profile first</h1>
        <p className="mx-auto mt-2 mb-6 max-w-md text-sm text-ink-soft">
          Conversations open once a match is made.
        </p>
        <Link
          href="/app/onboarding"
          className="bg-gradient-brand inline-block rounded-full px-7 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
        >
          Create a profile
        </Link>
      </div>
    );
  }

  function onDraftChange(value: string) {
    setDraft(value);
    if (selectedId && Date.now() - lastTypingSent.current > 2500) {
      lastTypingSent.current = Date.now();
      sendTyping(selectedId, true);
    }
  }

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || !selectedId) return;
    if (editing) {
      edit.mutate(
        { conversationId: selectedId, messageId: editing.id, body },
        { onSuccess: () => setEditing(null) },
      );
    } else {
      send.mutate({ conversationId: selectedId, body });
      sendTyping(selectedId, false);
    }
    setDraft("");
  }

  const items = messages.data?.items ?? [];
  const sendError = send.error ?? edit.error ?? remove.error;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="font-display text-[26px] font-bold tracking-tight">Messages</h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          Private, respectful conversations with your matches.
        </p>
      </header>

      <div className="glass grid min-h-[520px] grid-cols-1 overflow-hidden rounded-[26px] md:grid-cols-[280px_1fr]">
        {/* conversations pane */}
        <aside className="border-b border-glass-line md:border-r md:border-b-0">
          <ConversationList
            conversations={conversations.data?.items ?? []}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>

        {/* thread pane */}
        <section className="flex max-h-[70vh] flex-col">
          {!selectedId ? (
            <div className="grid flex-1 place-items-center p-10 text-center text-sm text-ink-soft">
              Select a conversation to start chatting.
            </div>
          ) : (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto p-5">
                {messages.isLoading && (
                  <p className="text-[13px] text-ink-soft">Loading messages…</p>
                )}
                {!messages.isLoading && items.length === 0 && (
                  <p className="pt-10 text-center text-[13px] text-ink-soft">
                    No messages yet — say Sat Sri Akal! 👋
                  </p>
                )}
                {items.map((m) => (
                  <MessageBubble
                    key={m.id}
                    mine={m.sender_profile_id === actingProfile.id}
                    body={m.body}
                    status={m.status}
                    time={m.created_at}
                    onEdit={() => {
                      setEditing({ id: m.id, body: m.body ?? "" });
                      setDraft(m.body ?? "");
                    }}
                    onDelete={() =>
                      remove.mutate({ conversationId: selectedId, messageId: m.id })
                    }
                  />
                ))}
                {peerTyping && (
                  <p className="text-[12px] text-ink-soft italic">typing…</p>
                )}
                <div ref={bottomRef} />
              </div>

              <div className="border-t border-glass-line p-4">
                {sendError != null && (
                  <p role="alert" className="mb-2 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
                    {authErrorMessage(sendError)}
                  </p>
                )}
                {editing && (
                  <p className="mb-2 flex items-center gap-2 text-[12px] text-ink-soft">
                    Editing message
                    <button
                      type="button"
                      onClick={() => {
                        setEditing(null);
                        setDraft("");
                      }}
                      className="cursor-pointer underline"
                    >
                      cancel
                    </button>
                  </p>
                )}
                <MessageAiToolbar
                  actingProfileId={actingProfile.id}
                  conversationId={selectedId}
                  draft={draft}
                  onUseText={setDraft}
                />
                <form onSubmit={onSubmit} className="flex gap-2.5">
                  <input
                    value={draft}
                    onChange={(e) => onDraftChange(e.target.value)}
                    placeholder="Write a message…"
                    maxLength={5000}
                    className="flex-1 rounded-full border border-glass-line bg-white/5 px-5 py-2.5 text-[14px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-primary"
                  />
                  <button
                    type="submit"
                    disabled={!draft.trim() || send.isPending || edit.isPending}
                    className="bg-gradient-brand cursor-pointer rounded-full px-6 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:opacity-50"
                  >
                    {editing ? "Save" : "Send"}
                  </button>
                </form>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <Suspense fallback={<p className="text-sm text-ink-soft">Loading…</p>}>
      <MessagesInner />
    </Suspense>
  );
}
