"use client";

/**
 * "Continue with phone" — passwordless OTP sign-in/signup via SMS (Amazon
 * SNS in production). Covers both new and returning users in one flow: a
 * brand-new phone number implicitly creates the account, a returning one
 * just gets a fresh login code — there's no separate password step at all.
 *
 * Same local-development convenience as the email flow: the dev-only
 * `/__dev__/verification-code` endpoint works for phone numbers too (it's
 * keyed by whatever string was sent to it), so this auto-prefills the code
 * fields when running against a local backend.
 */

import { useState } from "react";

import { Field, FormError } from "@/components/auth-form";
import { IS_LOCAL_API, api } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/lib/auth";

type Step = "phone" | "code";

export function PhoneAuthForm() {
  const { startPhoneAuth, verifyPhoneAndLogin } = useAuth();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [devFill, setDevFill] = useState<{ challenge_id: string; code: string } | null>(null);

  async function fetchDevCode(value: string) {
    try {
      const entry = await api.get<{ challenge_id: string; code: string }>(
        `/__dev__/verification-code?email=${encodeURIComponent(value)}`,
      );
      setDevFill(entry);
    } catch {
      setDevFill(null);
    }
  }

  async function onSendCode(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const challengeId = await startPhoneAuth(phone.trim());
      setChallengeId(challengeId);
      if (IS_LOCAL_API) await fetchDevCode(phone.trim());
      setStep("code");
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onVerify(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const data = new FormData(e.currentTarget);
    try {
      await verifyPhoneAndLogin(
        String(data.get("challengeId")).trim(),
        String(data.get("code")).trim(),
      );
      window.location.href = "/app";
    } catch (err) {
      setError(authErrorMessage(err));
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="glass mb-5 w-full cursor-pointer rounded-full py-2.5 text-[14px] font-semibold transition-transform hover:-translate-y-px"
      >
        Continue with phone
      </button>
    );
  }

  return (
    <div className="glass mb-5 rounded-xl p-4">
      <FormError message={error} />
      {step === "phone" ? (
        <form onSubmit={onSendCode} noValidate>
          <Field
            label="Phone number"
            name="phone"
            type="tel"
            autoComplete="tel"
            placeholder="+14155550123"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            hint="Include the country code, e.g. +1 for the US/Canada."
            required
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || !phone.trim()}
              className="bg-gradient-brand flex-1 cursor-pointer rounded-full py-2.5 text-[14px] font-semibold text-on-primary disabled:opacity-50"
            >
              {busy ? "Sending…" : "Send code"}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="cursor-pointer rounded-full border border-glass-line px-4 py-2.5 text-[13px] font-semibold text-ink-soft hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={onVerify} noValidate>
          {IS_LOCAL_API && devFill && (
            <div className="mb-4 rounded-xl bg-white/5 px-3.5 py-2.5 text-[12px] leading-relaxed text-ink-soft">
              <span className="font-semibold text-ink">Local development:</span>{" "}
              no real SMS is sent — the code below is pre-filled. Just hit verify.
            </div>
          )}
          <input
            type="hidden"
            name="challengeId"
            value={challengeId || devFill?.challenge_id || ""}
          />
          <Field
            key={devFill?.code ?? "code"}
            label="Verification code"
            name="code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="6-digit code"
            defaultValue={devFill?.code ?? ""}
            required
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="bg-gradient-brand flex-1 cursor-pointer rounded-full py-2.5 text-[14px] font-semibold text-on-primary disabled:opacity-50"
            >
              {busy ? "Verifying…" : "Verify and continue"}
            </button>
            <button
              type="button"
              onClick={() => setStep("phone")}
              className="cursor-pointer rounded-full border border-glass-line px-4 py-2.5 text-[13px] font-semibold text-ink-soft hover:text-ink"
            >
              Back
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
