"use client";

/** Hooks for Block 12 (Billing/entitlements, §13): plans, checkout,
 *  subscription, transactions, entitlements, promo codes. Account-scoped
 *  throughout (no acting_profile_id — billing belongs to the account, not
 *  a specific matchmaking profile). */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface Plan {
  id: string;
  name: string;
  price_cents: number;
  currency: string;
  interval: string;
}

export function usePlans() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: () => api.get<Plan[]>("/v1/plans"),
    staleTime: Infinity,
  });
}

export interface Subscription {
  plan_id: string;
  status: string;
  cancel_at_period_end: boolean;
  updated_at: string;
}

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: () => api.get<Subscription>("/v1/billing/subscription"),
  });
}

export function useCancelSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Subscription>("/v1/billing/subscription/cancel"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subscription"] }),
  });
}

export function useResumeSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Subscription>("/v1/billing/subscription/resume"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subscription"] }),
  });
}

export interface CheckoutSession {
  id: string;
  plan_id: string;
  status: string;
  checkout_url: string;
  created_at: string;
}

export function useCreateCheckoutSession() {
  return useMutation({
    mutationFn: (planId: string) =>
      api.post<CheckoutSession>("/v1/billing/checkout-sessions", { plan_id: planId }),
  });
}

export interface Transaction {
  id: string;
  type: string;
  amount_cents: number;
  currency: string;
  status: string;
  created_at: string;
}

export function useTransactions() {
  return useQuery({
    queryKey: ["transactions"],
    queryFn: () => api.get<{ items: Transaction[]; next_cursor: string | null }>(
      "/v1/billing/transactions?limit=50",
    ),
  });
}

export interface Entitlement {
  action: string;
  allowed: boolean;
  reason: string | null;
}

export function useEntitlements() {
  return useQuery({
    queryKey: ["entitlements"],
    queryFn: () => api.get<{ tier: string; entitlements: Entitlement[] }>("/v1/entitlements"),
  });
}

export function useRedeemPromo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      api.post<{ code: string; status: string; applied_at: string }>(
        "/v1/promo-redemptions",
        { code },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
      queryClient.invalidateQueries({ queryKey: ["entitlements"] });
    },
  });
}
