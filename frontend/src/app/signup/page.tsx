"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthCard, Field, FormError, SelectField, SubmitButton } from "@/components/auth-form";
import { GoogleSignInButton } from "@/components/google-signin-button";
import { PhoneAuthForm } from "@/components/phone-auth-form";
import { SiteNav } from "@/components/site-nav";
import { api, IS_LOCAL_API } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/lib/auth";

type Step = "register" | "verify";

const GENDERS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];

export default function SignUpPage() {
  const router = useRouter();
  const { register, verifyChallenge, signIn } = useAuth();
  const [step, setStep] = useState<Step>("register");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Held in memory so we can auto sign-in right after verification.
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null);
  // Challenge ID from backend, stored so we can pass it hidden to verify endpoint.
  const [challengeId, setChallengeId] = useState<string | null>(null);
  // Dev-only convenience: pre-filled from the backend's __dev__ endpoint.
  const [devFill, setDevFill] = useState<{ challenge_id: string; code: string } | null>(null);

  async function fetchDevCode(email: string) {
    // Only answers in local/development backends; harmless 404 otherwise.
    try {
      const entry = await api.get<{ challenge_id: string; code: string }>(
        `/__dev__/verification-code?email=${encodeURIComponent(email)}`,
      );
      setDevFill(entry);
    } catch {
      setDevFill(null);
    }
  }

  async function onRegister(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const data = new FormData(e.currentTarget);
    const displayName = String(data.get("displayName")).trim();
    const gender = String(data.get("gender") ?? "");
    const email = String(data.get("email"));
    const password = String(data.get("password"));
    try {
      const cid = await register(email, password, displayName, gender);
      setChallengeId(cid);
      setCredentials({ email, password });
      if (IS_LOCAL_API) await fetchDevCode(email);
      else setDevFill(null);
      setStep("verify");
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
      await verifyChallenge(
        String(data.get("challengeId")).trim(),
        String(data.get("code")).trim(),
      );
      if (credentials) {
        await signIn(credentials.email, credentials.password);
      }
      router.push("/app");
    } catch (err) {
      setError(authErrorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="relative z-10 mx-auto w-full max-w-[1180px] flex-1 px-5 sm:px-10">
      <SiteNav />
      <div className="flex justify-center pt-14 pb-20">
        {step === "register" ? (
          <AuthCard
            title="Create your account"
            subtitle="One account can manage profiles for yourself or your family."
          >
            <GoogleSignInButton onError={setError} />
            <PhoneAuthForm />
            <form onSubmit={onRegister} noValidate>
              <FormError message={error} />
              <Field
                label="Full name"
                name="displayName"
                type="text"
                autoComplete="name"
                placeholder="Your name"
                required
              />
              <SelectField label="Gender" name="gender" required defaultValue="">
                <option value="" disabled>
                  Select…
                </option>
                {GENDERS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </SelectField>
              <Field
                label="Email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
              />
              <Field
                label="Password"
                name="password"
                type="password"
                autoComplete="new-password"
                placeholder="At least 10 characters"
                minLength={10}
                hint="Use 10+ characters — a short phrase works well."
                required
              />
              <SubmitButton busy={busy}>Create account</SubmitButton>
            </form>
            <p className="mt-6 text-center text-[13.5px] text-ink-soft">
              Already have an account?{" "}
              <Link href="/signin" className="font-semibold text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </AuthCard>
        ) : (
          <AuthCard
            title="Verify your email"
            subtitle="Enter the 6-digit verification code we sent to your email address."
          >
            {IS_LOCAL_API && devFill && (
              <div className="glass mb-5 rounded-xl px-4 py-3 text-[12.5px] leading-relaxed text-ink-soft">
                <span className="font-semibold text-ink">Local development:</span>{" "}
                no real email is sent — the code below is pre-filled straight
                from the dev server. Just hit verify.
              </div>
            )}
            <form onSubmit={onVerify} noValidate>
              <FormError message={error} />
              <input type="hidden" name="challengeId" value={challengeId || devFill?.challenge_id || ""} />
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
              <SubmitButton busy={busy}>Verify and sign in</SubmitButton>
            </form>
          </AuthCard>
        )}
      </div>
    </div>
  );
}
