// Billing & plan-gating. Stripe-ready architecture; no Stripe wiring yet.
// Plan source today: localStorage (mirrors profile.plan in store).
// When Stripe lands, swap `readPlan()` to hydrate from `user_subscriptions`.

import { useEffect, useState } from "react";
import { useAppState } from "./store";

export type Plan = "free" | "pro";

export interface PlanLimits {
  monthlySingleAnalyses: number | "unlimited";
  fullSetAnalysis: boolean;
  advancedCoachFeedback: boolean;
  fullHistory: boolean;
  skillTree: boolean;
  weeklyTrainingPlan: boolean;
}

export const PLAN_LIMITS: Record<Plan, PlanLimits> = {
  free: {
    monthlySingleAnalyses: 3,
    fullSetAnalysis: false,
    advancedCoachFeedback: false,
    fullHistory: false,
    skillTree: false,
    weeklyTrainingPlan: false,
  },
  pro: {
    monthlySingleAnalyses: "unlimited",
    fullSetAnalysis: true,
    advancedCoachFeedback: true,
    fullHistory: true,
    skillTree: true,
    weeklyTrainingPlan: true,
  },
};

export const PRO_PRICE_MONTHLY_USD = 12;

// ─────────────────────────────────────────────────────────────────────────
// TESTPHASE: Paywall deaktiviert — alle Features und unbegrenzte Analysen
// fuer alle Nutzer. Fuer den Launch einfach auf `false` setzen, dann
// greifen die PLAN_LIMITS oben wieder. Die gesamte Billing-Architektur
// bleibt intakt (LockedFeature, UpgradeModal, Stripe-Stub).
// ─────────────────────────────────────────────────────────────────────────
export const PAYWALL_DISABLED = true;

// Open the upgrade modal from anywhere via a window event.
const UPGRADE_EVENT = "mixcoach:upgrade-modal";

export function openUpgradeModal(reason?: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(UPGRADE_EVENT, { detail: { reason } }));
}

export function onOpenUpgradeModal(cb: (reason?: string) => void) {
  if (typeof window === "undefined") return () => {};
  const handler = (e: Event) => cb((e as CustomEvent).detail?.reason);
  window.addEventListener(UPGRADE_EVENT, handler as EventListener);
  return () => window.removeEventListener(UPGRADE_EVENT, handler as EventListener);
}

// Map legacy plan field "premium" → "pro" so existing accounts stay upgraded.
function normalize(p: string | undefined): Plan {
  return p === "pro" || p === "premium" ? "pro" : "free";
}

export function usePlan(): { plan: Plan; isPro: boolean; limits: PlanLimits; setPlan: (p: Plan) => void } {
  const [state, update] = useAppState();
  const plan = PAYWALL_DISABLED ? "pro" : normalize(state.profile.plan);
  return {
    plan,
    isPro: plan === "pro",
    limits: PLAN_LIMITS[plan],
    setPlan: (next) =>
      update((s) => ({ ...s, profile: { ...s.profile, plan: next === "pro" ? "premium" : "free" } })),
  };
}

// Usage counter — counts analyses created in the current calendar month.
export function useMonthlyUsage(): { used: number; cap: number | "unlimited"; remaining: number | "unlimited"; capped: boolean } {
  const [state] = useAppState();
  const { limits } = usePlan();
  const now = new Date();
  const m = now.getMonth();
  const y = now.getFullYear();
  const used = state.analyses.filter((a) => {
    const ts = new Date(a.createdAt ?? Date.now());
    return ts.getMonth() === m && ts.getFullYear() === y;
  }).length;
  const cap = limits.monthlySingleAnalyses;
  if (cap === "unlimited") return { used, cap, remaining: "unlimited", capped: false };
  return { used, cap, remaining: Math.max(0, cap - used), capped: used >= cap };
}

// ── Stripe-ready stub ────────────────────────────────────────────────────────
// When Stripe lands: implement createCheckoutSession() as a server fn that
// creates a Stripe Checkout session and returns its URL; webhook updates
// public.user_subscriptions; client just calls this and redirects.
export async function startUpgradeCheckout(_plan: "pro" = "pro"): Promise<{ url: string | null; status: "stub" }> {
  return { url: null, status: "stub" };
}

// Toggle to flip the auth surface into waitlist-only mode for the private beta.
export const WAITLIST_MODE =
  typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_WAITLIST_MODE === "true";
