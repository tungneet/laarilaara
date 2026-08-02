"use client";

/** Notification center (Block 10, §12): inbox list + delivery preferences.
 *  Account-scoped (no acting profile needed) — an in-app inbox belongs to
 *  the logged-in account, not a specific matchmaking profile. */

import { useState } from "react";

import { authErrorMessage } from "@/lib/auth";
import {
  NOTIFICATION_CATEGORIES,
  NOTIFICATION_CHANNELS,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotificationPreferences,
  useNotifications,
  useUpdateNotificationPreferences,
  type Notification,
} from "@/lib/notifications";

const CATEGORY_LABEL: Record<string, string> = {
  match: "Matches",
  message: "Messages",
  interest: "Interests",
  moderation: "Moderation",
  system: "System",
};

const CHANNEL_LABEL: Record<string, string> = {
  in_app: "In-app",
  email: "Email",
  push: "Push",
};

function NotificationRow({ notification }: { notification: Notification }) {
  const markRead = useMarkNotificationRead();
  const unread = notification.read_at === null;

  return (
    <li
      className={`glass rounded-card flex items-start justify-between gap-4 p-4 ${unread ? "border-l-2 border-primary" : ""}`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2.5">
          <span className="rounded-full bg-primary-soft px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase">
            {CATEGORY_LABEL[notification.category] ?? notification.category}
          </span>
          <span className="text-[12px] text-ink-soft">
            {new Date(notification.created_at).toLocaleString()}
          </span>
          {unread && (
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-label="Unread" />
          )}
        </div>
        <p className="mt-1.5 text-[14px] font-semibold">{notification.title}</p>
        <p className="mt-0.5 text-[13px] leading-relaxed text-ink-soft">{notification.body}</p>
      </div>
      {unread && (
        <button
          type="button"
          disabled={markRead.isPending}
          onClick={() => markRead.mutate(notification.id)}
          className="glass shrink-0 cursor-pointer rounded-full px-4 py-1.5 text-[12.5px] font-semibold transition-transform hover:-translate-y-px disabled:opacity-60"
        >
          {markRead.isPending ? "…" : "Mark read"}
        </button>
      )}
    </li>
  );
}

function PreferencesPanel() {
  const prefs = useNotificationPreferences();
  const update = useUpdateNotificationPreferences();
  const [draft, setDraft] = useState<Record<string, string[]> | null>(null);
  const [saved, setSaved] = useState(false);

  const categories = draft ?? prefs.data?.categories ?? {};

  function toggle(category: string, channel: string) {
    const current = categories[category] ?? [];
    const next = current.includes(channel)
      ? current.filter((c) => c !== channel)
      : [...current, channel];
    setDraft({ ...categories, [category]: next });
    setSaved(false);
  }

  if (prefs.isLoading) return <p className="text-sm text-ink-soft">Loading preferences…</p>;

  return (
    <div className="glass rounded-card p-5">
      <h2 className="font-display text-[17px] font-bold">Delivery preferences</h2>
      <p className="mt-1 text-[13px] text-ink-soft">
        Choose how you want to be notified for each type of update.
      </p>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[420px] border-collapse text-left">
          <thead>
            <tr>
              <th className="pb-2 text-[12px] font-medium text-ink-soft">Category</th>
              {NOTIFICATION_CHANNELS.map((channel) => (
                <th key={channel} className="pb-2 text-center text-[12px] font-medium text-ink-soft">
                  {CHANNEL_LABEL[channel]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {NOTIFICATION_CATEGORIES.map((category) => (
              <tr key={category} className="border-t border-glass-line">
                <td className="py-2.5 text-[13.5px] font-medium">
                  {CATEGORY_LABEL[category]}
                </td>
                {NOTIFICATION_CHANNELS.map((channel) => {
                  const active = (categories[category] ?? []).includes(channel);
                  return (
                    <td key={channel} className="py-2.5 text-center">
                      <button
                        type="button"
                        aria-pressed={active}
                        onClick={() => toggle(category, channel)}
                        className={`h-6 w-6 cursor-pointer rounded-full border transition-colors ${
                          active
                            ? "border-primary bg-primary"
                            : "border-glass-line bg-transparent"
                        }`}
                        aria-label={`${CATEGORY_LABEL[category]} via ${CHANNEL_LABEL[channel]}`}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {update.isError && (
        <p role="alert" className="mt-3 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
          {authErrorMessage(update.error)}
        </p>
      )}

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          disabled={!draft || update.isPending}
          onClick={() =>
            update.mutate(categories, {
              onSuccess: () => {
                setDraft(null);
                setSaved(true);
              },
            })
          }
          className="bg-gradient-brand cursor-pointer rounded-full px-6 py-2 text-[13px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110 disabled:opacity-40"
        >
          {update.isPending ? "Saving…" : "Save preferences"}
        </button>
        {saved && !draft && (
          <span className="text-[12.5px] text-ink-soft">Saved ✓</span>
        )}
      </div>
    </div>
  );
}

export default function NotificationsPage() {
  const notifications = useNotifications();
  const markAllRead = useMarkAllNotificationsRead();

  const items = notifications.data?.items ?? [];
  const unreadCount = items.filter((n) => n.read_at === null).length;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-[26px] font-bold tracking-tight">Notifications</h1>
          <p className="mt-0.5 text-sm text-ink-soft">
            {unreadCount > 0
              ? `${unreadCount} unread notification${unreadCount === 1 ? "" : "s"}`
              : "You're all caught up."}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            type="button"
            disabled={markAllRead.isPending}
            onClick={() => markAllRead.mutate()}
            className="glass cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold transition-transform hover:-translate-y-px disabled:opacity-60"
          >
            {markAllRead.isPending ? "Marking…" : "Mark all read"}
          </button>
        )}
      </header>

      {notifications.isLoading ? (
        <p className="text-sm text-ink-soft">Loading…</p>
      ) : items.length === 0 ? (
        <div className="glass rounded-[26px] p-10 text-center">
          <h2 className="font-display text-[18px] font-bold">No notifications yet</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-ink-soft">
            Updates about your matches, messages, and interests will show up here.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <NotificationRow key={n.id} notification={n} />
          ))}
        </ul>
      )}

      <PreferencesPanel />
    </div>
  );
}
