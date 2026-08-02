"use client";

/** Billing & entitlements (Block 12, §13): plans, checkout, subscription,
 *  transactions, entitlements, promo codes. Account-scoped (no acting
 *  profile involved). Payments are simulated — checkout sessions never
 *  leave `status=pending` (documented backend simplification, no real
 *  payment provider is wired up yet). */

import { useState } from "react";

import { SectionCard } from "@/components/profile-editor/section-card";
import {
  useCancelSubscription,
  useCreateCheckoutSession,
  useEntitlements,
  usePlans,
  useRedeemPromo,
  useResumeSubscription,
  useSubscription,
  useTransactions,
  type Plan,
} from "@/lib/billing";

function formatMoney(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(cents / 100);
}

const ACTION_LABEL: Record<string, string> = {
  send_interest: "Send interest",
  start_conversation: "Start a conversation",
  run_ai_draft: "Use AI drafting tools",
  advanced_search: "Advanced search filters",
  see_who_viewed_me: "See who viewed your profile",
};

function PlanCard({
  plan,
  isCurrent,
  onChoose,
  busy,
}: {
  plan: Plan;
  isCurrent: boolean;
  onChoose: () => void;
  busy: boolean;
}) {
  return (
    <div
      className={`glass rounded-card flex flex-col gap-3 p-5 ${isCurrent ? "border border-primary" : ""}`}
    >
      <div>
        <h3 className="font-display text-[16px] font-semibold">{plan.name}</h3>
        <p className="mt-1 text-[22px] font-bold">
          {formatMoney(plan.price_cents, plan.currency)}
          <span className="text-[13px] font-normal text-ink-soft"> / {plan.interval}</span>
        </p>
      </div>
      {isCurrent ? (
        <span className="mt-auto self-start rounded-full bg-primary-soft px-3 py-1 text-[12px] font-semibold">
          Current plan
        </span>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={onChoose}
          className="bg-gradient-brand mt-auto cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "Redirecting…" : plan.price_cents === 0 ? "Switch to Free" : "Choose plan"}
        </button>
      )}
    </div>
  );
}

function PlansSection() {
  const plans = usePlans();
  const subscription = useSubscription();
  const checkout = useCreateCheckoutSession();
  const cancel = useCancelSubscription();
  const resume = useResumeSubscription();

  return (
    <SectionCard
      title="Plan"
      description="Simulated checkout — no real payment provider is connected yet."
      error={checkout.error ?? cancel.error ?? resume.error}
    >
      {plans.isLoading || subscription.isLoading ? (
        <p className="text-[13px] text-ink-soft">Loading…</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {(plans.data ?? []).map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                isCurrent={plan.id === subscription.data?.plan_id}
                busy={checkout.isPending}
                onChoose={() => checkout.mutate(plan.id)}
              />
            ))}
          </div>

          {checkout.data && (
            <p className="mt-4 text-[12.5px] text-ink-soft">
              Checkout session created (status: {checkout.data.status}) — no real payment provider
              is wired up, so this stays simulated.
            </p>
          )}

          {subscription.data && subscription.data.plan_id !== "free" && (
            <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-glass-line pt-4">
              <p className="text-[13px] text-ink-soft">
                {subscription.data.cancel_at_period_end
                  ? "Your plan will not renew at the end of the current period."
                  : "Your plan renews automatically."}
              </p>
              {subscription.data.cancel_at_period_end ? (
                <button
                  type="button"
                  disabled={resume.isPending}
                  onClick={() => resume.mutate()}
                  className="glass cursor-pointer rounded-full px-4 py-1.5 text-[12.5px] font-semibold disabled:opacity-60"
                >
                  {resume.isPending ? "Resuming…" : "Resume auto-renew"}
                </button>
              ) : (
                <button
                  type="button"
                  disabled={cancel.isPending}
                  onClick={() => cancel.mutate()}
                  className="cursor-pointer rounded-full bg-accent-soft px-4 py-1.5 text-[12.5px] font-semibold disabled:opacity-60"
                >
                  {cancel.isPending ? "Cancelling…" : "Cancel auto-renew"}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </SectionCard>
  );
}

function EntitlementsSection() {
  const entitlements = useEntitlements();

  return (
    <SectionCard title="What's included" description="Your current capability access.">
      {entitlements.isLoading ? (
        <p className="text-[13px] text-ink-soft">Loading…</p>
      ) : (
        <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {(entitlements.data?.entitlements ?? []).map((e) => (
            <li
              key={e.action}
              className="glass flex items-center justify-between gap-3 rounded-xl px-4 py-2.5 text-[13px]"
            >
              <span>{ACTION_LABEL[e.action] ?? e.action}</span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase ${
                  e.allowed ? "bg-primary-soft" : "bg-accent-soft"
                }`}
              >
                {e.allowed ? "Included" : "Locked"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

function PromoSection() {
  const redeem = useRedeemPromo();
  const [code, setCode] = useState("");

  return (
    <SectionCard
      title="Promo code"
      description="Have a code? Redeem it here."
      error={redeem.error}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="e.g. WELCOME10"
          maxLength={64}
          className="min-w-[200px] flex-1 rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] outline-none focus:border-primary"
        />
        <button
          type="button"
          disabled={redeem.isPending || !code}
          onClick={() => redeem.mutate(code, { onSuccess: () => setCode("") })}
          className="bg-gradient-brand cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold text-on-primary disabled:opacity-40"
        >
          {redeem.isPending ? "Applying…" : "Redeem"}
        </button>
      </div>
      {redeem.data && (
        <p className="mt-3 text-[12.5px] text-ink-soft">
          Applied {redeem.data.code} — {redeem.data.status}.
        </p>
      )}
    </SectionCard>
  );
}

function TransactionsSection() {
  const transactions = useTransactions();
  const items = transactions.data?.items ?? [];

  return (
    <SectionCard title="Billing history" description="Your past transactions.">
      {transactions.isLoading ? (
        <p className="text-[13px] text-ink-soft">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-[13px] text-ink-soft">No transactions yet.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((t) => (
            <li key={t.id} className="glass flex items-center justify-between rounded-xl px-4 py-2.5">
              <div>
                <p className="text-[13px] font-medium capitalize">{t.type}</p>
                <p className="text-[12px] text-ink-soft">{new Date(t.created_at).toLocaleString()}</p>
              </div>
              <div className="text-right">
                <p className="text-[13px] font-semibold">{formatMoney(t.amount_cents, t.currency)}</p>
                <p className="text-[11px] text-ink-soft uppercase">{t.status}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export default function BillingPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[26px] font-bold tracking-tight">Billing</h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          Manage your plan, view what&apos;s included, and check your billing history.
        </p>
      </header>

      <PlansSection />
      <EntitlementsSection />
      <PromoSection />
      <TransactionsSection />
    </div>
  );
}
