"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthCard, Field, FormError, SubmitButton } from "@/components/auth-form";
import { SiteNav } from "@/components/site-nav";
import { authErrorMessage, useAuth } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const data = new FormData(e.currentTarget);
    try {
      await signIn(String(data.get("email")), String(data.get("password")));
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
        <AuthCard
          title="Welcome back"
          subtitle="Sign in to continue your family's search."
        >
          <form onSubmit={onSubmit} noValidate>
            <FormError message={error} />
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
              autoComplete="current-password"
              placeholder="••••••••••"
              required
            />
            <SubmitButton busy={busy}>Sign in</SubmitButton>
          </form>
          <p className="mt-6 text-center text-[13.5px] text-ink-soft">
            New to LaariLaara?{" "}
            <Link href="/signup" className="font-semibold text-primary hover:underline">
              Create an account
            </Link>
          </p>
        </AuthCard>
      </div>
    </div>
  );
}
