"use client";

/** Settings (Block 11, §4): account/locale, sessions, contacts, password
 *  reset, and data requests. Account-scoped throughout — no acting profile
 *  is involved, unlike most other domains. */

import { useState } from "react";
import { useRouter } from "next/navigation";

import { SectionCard, SaveButton } from "@/components/profile-editor/section-card";
import { useAuth } from "@/lib/auth";
import {
  useAddContact,
  useContacts,
  useCreateDataRequest,
  useDataRequests,
  useRemoveContact,
  useRequestPasswordReset,
  useResetPassword,
  useRevokeSession,
  useSessions,
  useUpdateLocale,
  useVerifyContact,
  type ContactType,
  type DataRequestType,
} from "@/lib/settings";

const LOCALES = [
  { value: "en-US", label: "English (US)" },
  { value: "en-GB", label: "English (UK)" },
  { value: "en-CA", label: "English (Canada)" },
  { value: "pa-IN", label: "Punjabi" },
];

function AccountSection() {
  const { account, refreshAccount } = useAuth();
  const update = useUpdateLocale();
  const [locale, setLocale] = useState(account?.locale ?? "en-US");
  const [saved, setSaved] = useState(false);

  if (!account) return null;

  return (
    <SectionCard
      title="Account"
      description="Your login email and regional preferences."
      saved={saved}
      error={update.error}
    >
      <div className="mb-4 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
        <div>
          <span className="mb-1 block text-[13px] font-medium text-ink-soft">Name</span>
          <p className="text-[14px]">{account.display_name || "—"}</p>
        </div>
        <div>
          <span className="mb-1 block text-[13px] font-medium text-ink-soft">Gender</span>
          <p className="text-[14px] capitalize">{account.gender || "—"}</p>
        </div>
        <div>
          <span className="mb-1 block text-[13px] font-medium text-ink-soft">Email</span>
          <p className="text-[14px]">{account.email}</p>
        </div>
        <div>
          <span className="mb-1 block text-[13px] font-medium text-ink-soft">Plan</span>
          <p className="text-[14px] capitalize">{account.tier}</p>
        </div>
      </div>
      <label className="mb-4 block max-w-xs text-[13px] font-medium text-ink-soft">
        Locale
        <select
          value={locale}
          onChange={(e) => {
            setLocale(e.target.value);
            setSaved(false);
          }}
          className="mt-1.5 w-full rounded-lg border border-glass-line bg-[var(--bg-a)] px-3.5 py-2.5 text-[13.5px] text-ink outline-none focus:border-primary"
        >
          {LOCALES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        disabled={update.isPending || locale === account.locale}
        onClick={() =>
          update.mutate(locale, {
            onSuccess: async () => {
              setSaved(true);
              await refreshAccount();
            },
          })
        }
        className="bg-gradient-brand cursor-pointer rounded-full px-6 py-2 text-[13px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110 disabled:cursor-default disabled:opacity-40"
      >
        {update.isPending ? "Saving…" : "Save locale"}
      </button>
    </SectionCard>
  );
}

function SessionsSection() {
  const sessions = useSessions();
  const revoke = useRevokeSession();
  const { signOutAll } = useAuth();
  const router = useRouter();
  const [signingOutAll, setSigningOutAll] = useState(false);

  return (
    <SectionCard title="Active sessions" description="Devices currently signed in to your account.">
      {sessions.isLoading ? (
        <p className="text-[13px] text-ink-soft">Loading…</p>
      ) : (
        <ul className="space-y-2.5">
          {(sessions.data ?? []).map((s) => (
            <li
              key={s.id}
              className="glass flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3"
            >
              <div>
                <p className="text-[13.5px] font-medium">
                  {s.is_current ? "This device" : "Other device"}
                </p>
                <p className="text-[12px] text-ink-soft">
                  Signed in {new Date(s.created_at).toLocaleString()} · expires{" "}
                  {new Date(s.expires_at).toLocaleDateString()}
                </p>
              </div>
              {!s.is_current && (
                <button
                  type="button"
                  disabled={revoke.isPending}
                  onClick={() => revoke.mutate(s.id)}
                  className="cursor-pointer rounded-full bg-accent-soft px-4 py-1.5 text-[12.5px] font-semibold disabled:opacity-60"
                >
                  Sign out
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {(sessions.data?.length ?? 0) > 1 && (
        <button
          type="button"
          disabled={signingOutAll}
          onClick={async () => {
            setSigningOutAll(true);
            try {
              await signOutAll();
              router.push("/signin");
            } finally {
              setSigningOutAll(false);
            }
          }}
          className="mt-4 cursor-pointer rounded-full border border-glass-line px-5 py-2 text-[12.5px] font-semibold text-ink-soft transition-colors hover:border-primary hover:text-ink disabled:opacity-60"
        >
          {signingOutAll ? "Signing out…" : "Sign out of all devices"}
        </button>
      )}
    </SectionCard>
  );
}

function ContactsSection() {
  const contacts = useContacts();
  const add = useAddContact();
  const verify = useVerifyContact();
  const remove = useRemoveContact();
  const [type, setType] = useState<ContactType>("email");
  const [value, setValue] = useState("");
  const [verifying, setVerifying] = useState<string | null>(null);
  const [code, setCode] = useState("");

  return (
    <SectionCard
      title="Contacts"
      description="Alternate ways to reach you and recover your account."
      error={add.error ?? verify.error ?? remove.error}
    >
      <ul className="mb-4 space-y-2.5">
        {(contacts.data ?? []).map((c) => (
          <li key={c.id} className="glass rounded-xl px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[13.5px] font-medium">
                  {c.masked_value}{" "}
                  <span className="text-[11px] font-normal text-ink-soft uppercase">{c.type}</span>
                </p>
                <p className="text-[12px] text-ink-soft">
                  {c.verified ? "Verified" : "Not yet verified"}
                </p>
              </div>
              <div className="flex gap-2">
                {!c.verified && (
                  <button
                    type="button"
                    onClick={() => setVerifying(verifying === c.id ? null : c.id)}
                    className="cursor-pointer rounded-full bg-primary-soft px-4 py-1.5 text-[12.5px] font-semibold"
                  >
                    Verify
                  </button>
                )}
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(c.id)}
                  className="cursor-pointer rounded-full bg-accent-soft px-4 py-1.5 text-[12.5px] font-semibold disabled:opacity-60"
                >
                  Remove
                </button>
              </div>
            </div>
            {verifying === c.id && (
              <div className="mt-3 flex gap-2">
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Verification code"
                  maxLength={16}
                  className="flex-1 rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
                />
                <button
                  type="button"
                  disabled={verify.isPending}
                  onClick={() =>
                    verify.mutate(
                      { contactId: c.id, code },
                      { onSuccess: () => { setVerifying(null); setCode(""); } },
                    )
                  }
                  className="cursor-pointer rounded-full bg-primary px-4 py-2 text-[12.5px] font-semibold text-on-primary disabled:opacity-60"
                >
                  Confirm
                </button>
              </div>
            )}
          </li>
        ))}
        {contacts.data?.length === 0 && (
          <p className="text-[13px] text-ink-soft">No contacts added yet.</p>
        )}
      </ul>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={type}
          onChange={(e) => setType(e.target.value as ContactType)}
          className="rounded-lg border border-glass-line bg-[var(--bg-a)] px-3 py-2 text-[13px] outline-none focus:border-primary"
        >
          <option value="email">Email</option>
          <option value="phone">Phone</option>
        </select>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={type === "email" ? "you@example.com" : "+1 555 0100"}
          className="min-w-[200px] flex-1 rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
        />
        <button
          type="button"
          disabled={add.isPending || !value}
          onClick={() => add.mutate({ type, value }, { onSuccess: () => setValue("") })}
          className="bg-gradient-brand cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold text-on-primary disabled:opacity-40"
        >
          Add
        </button>
      </div>
    </SectionCard>
  );
}

function PasswordSection() {
  const { account } = useAuth();
  const requestReset = useRequestPasswordReset();
  const resetPassword = useResetPassword();
  const [challengeId, setChallengeId] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [done, setDone] = useState(false);

  if (!account) return null;

  return (
    <SectionCard
      title="Password"
      description="We'll email a verification code to confirm the change."
      error={requestReset.error ?? resetPassword.error}
    >
      {done ? (
        <p className="text-[13.5px] text-ink-soft">Password updated ✓</p>
      ) : !sent ? (
        <button
          type="button"
          disabled={requestReset.isPending}
          onClick={() =>
            requestReset.mutate(account.email, { onSuccess: () => setSent(true) })
          }
          className="glass cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold disabled:opacity-60"
        >
          {requestReset.isPending ? "Sending…" : "Send password reset code"}
        </button>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            resetPassword.mutate(
              { challengeId, code, newPassword },
              { onSuccess: () => setDone(true) },
            );
          }}
          className="max-w-sm space-y-3"
        >
          <input
            value={challengeId}
            onChange={(e) => setChallengeId(e.target.value)}
            placeholder="Challenge ID (from the reset email)"
            required
            className="w-full rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
          />
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Verification code"
            required
            className="w-full rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password"
            required
            minLength={8}
            className="w-full rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
          />
          <SaveButton busy={resetPassword.isPending} label="Update password" />
        </form>
      )}
    </SectionCard>
  );
}

const DATA_REQUEST_LABEL: Record<string, string> = {
  export: "Export my data",
  correction: "Request a correction",
  deletion: "Delete my account data",
};

function DataPrivacySection() {
  const { account } = useAuth();
  const requests = useDataRequests(account?.id);
  const create = useCreateDataRequest(account?.id);
  const [type, setType] = useState<DataRequestType>("export");
  const [details, setDetails] = useState("");

  return (
    <SectionCard
      title="Data & privacy"
      description="Request an export, correction, or deletion of your data."
      error={create.error}
    >
      <div className="mb-5 flex flex-wrap items-end gap-2.5">
        <label className="text-[13px] font-medium text-ink-soft">
          Request type
          <select
            value={type}
            onChange={(e) => setType(e.target.value as DataRequestType)}
            className="mt-1.5 block rounded-lg border border-glass-line bg-[var(--bg-a)] px-3 py-2 text-[13px] outline-none focus:border-primary"
          >
            <option value="export">Export my data</option>
            <option value="correction">Request a correction</option>
            <option value="deletion">Delete my account data</option>
          </select>
        </label>
        <input
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          placeholder="Optional details"
          maxLength={2000}
          className="min-w-[220px] flex-1 rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
        />
        <button
          type="button"
          disabled={create.isPending}
          onClick={() => create.mutate({ type, details }, { onSuccess: () => setDetails("") })}
          className="bg-gradient-brand cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold text-on-primary disabled:opacity-40"
        >
          {create.isPending ? "Submitting…" : "Submit request"}
        </button>
      </div>

      {requests.data && requests.data.length > 0 && (
        <ul className="space-y-2">
          {requests.data.map((r) => (
            <li key={r.id} className="glass flex items-center justify-between rounded-xl px-4 py-2.5">
              <div>
                <p className="text-[13px] font-medium">{DATA_REQUEST_LABEL[r.type] ?? r.type}</p>
                <p className="text-[12px] text-ink-soft">
                  {new Date(r.created_at).toLocaleDateString()}
                  {r.details ? ` · ${r.details}` : ""}
                </p>
              </div>
              <span className="rounded-full bg-primary-soft px-2.5 py-1 text-[11px] font-semibold uppercase">
                {r.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export default function SettingsPage() {
  const { loading } = useAuth();

  if (loading) return <p className="text-sm text-ink-soft">Loading…</p>;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[26px] font-bold tracking-tight">Settings</h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          Manage your account, security, contacts, and data.
        </p>
      </header>

      <AccountSection />
      <SessionsSection />
      <ContactsSection />
      <PasswordSection />
      <DataPrivacySection />
    </div>
  );
}

