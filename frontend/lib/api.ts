import type {
  CartExecutionRequest,
  CartExecutionResult,
  CookieEntry,
  CookieStatus,
  HouseholdProfile,
  PlanRequest,
  ShoppingPlan,
  ShoppingRules,
  ShoppingSession,
  AvoidRule,
  BrandRule,
  PricePreference,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Shopping
export const api = {
  shopping: {
    createPlan: (req: PlanRequest) =>
      fetchJSON<ShoppingPlan>("/api/shopping/plan", {
        method: "POST",
        body: JSON.stringify(req),
      }),

    listSessions: (limit = 50, offset = 0) =>
      fetchJSON<ShoppingSession[]>(`/api/shopping/sessions?limit=${limit}&offset=${offset}`),

    getSession: (sessionId: string) =>
      fetchJSON<ShoppingPlan>(`/api/shopping/sessions/${sessionId}`),
  },

  cart: {
    execute: (req: CartExecutionRequest) =>
      fetchJSON<CartExecutionResult>("/api/cart/execute", {
        method: "POST",
        body: JSON.stringify(req),
      }),

    streamStatus: (executionId: string): EventSource =>
      new EventSource(`${BASE_URL}/api/cart/status/${executionId}`),
  },

  rules: {
    get: () => fetchJSON<ShoppingRules>("/api/rules"),

    update: (rules: ShoppingRules) =>
      fetchJSON<ShoppingRules>("/api/rules", {
        method: "PUT",
        body: JSON.stringify(rules),
      }),

    updateAvoid: (avoid: AvoidRule[]) =>
      fetchJSON<ShoppingRules>("/api/rules/avoid", {
        method: "PATCH",
        body: JSON.stringify(avoid),
      }),

    updateBrands: (brands: BrandRule[]) =>
      fetchJSON<ShoppingRules>("/api/rules/brands", {
        method: "PATCH",
        body: JSON.stringify(brands),
      }),

    updatePreferences: (price: PricePreference) =>
      fetchJSON<ShoppingRules>("/api/rules/preferences", {
        method: "PATCH",
        body: JSON.stringify(price),
      }),
  },

  profile: {
    get: () => fetchJSON<HouseholdProfile>("/api/profile"),

    update: (profile: HouseholdProfile) =>
      fetchJSON<HouseholdProfile>("/api/profile", {
        method: "PUT",
        body: JSON.stringify(profile),
      }),
  },

  settings: {
    getCookieStatus: () => fetchJSON<CookieStatus>("/api/settings/cookies/status"),

    uploadCookies: (cookies: CookieEntry[]) =>
      fetchJSON<CookieStatus>("/api/settings/cookies", {
        method: "POST",
        body: JSON.stringify({ cookies }),
      }),

    deleteCookies: () =>
      fetchJSON<{ message: string }>("/api/settings/cookies", {
        method: "DELETE",
      }),
  },
};
