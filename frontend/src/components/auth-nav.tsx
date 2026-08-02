"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

/** Right-hand nav slot: "Sign in" when logged out, account + sign out when in. */
export function AuthNavSlot() {
  const router = useRouter();
  const { account, loading, signOut } = useAuth();

  if (loading) {
    return <div className="glass h-10 w-24 animate-pulse rounded-full" />;
  }

  if (!account) {
    return (
      <Link
        href="/signin"
        className="glass rounded-full px-6 py-2.5 text-sm font-semibold transition-transform duration-150 hover:-translate-y-px"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2.5">
      <Link
        href="/app"
        className="bg-gradient-brand rounded-full px-5 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
      >
        Open app
      </Link>
      <button
        type="button"
        onClick={async () => {
          await signOut();
          router.push("/");
        }}
        className="glass cursor-pointer rounded-full px-5 py-2.5 text-sm font-semibold transition-transform duration-150 hover:-translate-y-px"
      >
        Sign out
      </button>
    </div>
  );
}
