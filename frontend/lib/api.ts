import type {
  CartExecutionRequest,
  CartExecutionResult,
  CookieEntry,
  CookieStatus,
  HouseholdProfile,
  PlanRequest,
  ShoppingItem,
  ShoppingPlan,
  ShoppingRules,
  ShoppingSession,
  AvoidRule,
  BrandRule,
  PricePreference,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token = sessionStorage.getItem("api_secret_key");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: getAuthHeaders(),
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

    updateItems: (sessionId: string, items: ShoppingItem[]) =>
      fetchJSON<ShoppingPlan>(`/api/shopping/sessions/${sessionId}/items`, {
        method: "PUT",
        body: JSON.stringify({ items }),
      }),

    addItem: (sessionId: string, item: ShoppingItem) =>
      fetchJSON<ShoppingPlan>(`/api/shopping/sessions/${sessionId}/items`, {
        method: "POST",
        body: JSON.stringify({ item }),
      }),

    removeItem: (sessionId: string, itemIndex: number) =>
      fetchJSON<ShoppingPlan>(`/api/shopping/sessions/${sessionId}/items/${itemIndex}`, {
        method: "DELETE",
      }),

    updateItem: (sessionId: string, itemIndex: number, item: ShoppingItem) =>
      fetchJSON<ShoppingPlan>(`/api/shopping/sessions/${sessionId}/items/${itemIndex}`, {
        method: "PATCH",
        body: JSON.stringify(item),
      }),

    reuseSession: (sessionId: string) =>
      fetchJSON<ShoppingPlan>("/api/shopping/reuse", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
      }),
  },

  cart: {
    execute: (req: CartExecutionRequest) =>
      fetchJSON<CartExecutionResult>("/api/cart/execute", {
        method: "POST",
        body: JSON.stringify(req),
      }),

    streamStatus: (executionId: string): EventSource => {
      const url = new URL(`${BASE_URL}/api/cart/status/${executionId}`);
      if (typeof window !== "undefined") {
        const token = sessionStorage.getItem("api_secret_key");
        if (token) {
          url.searchParams.set("token", token);
        }
      }
      return new EventSource(url.toString());
    },

    getExecutions: (sessionId: string) =>
      fetchJSON<CartExecutionResult[]>(`/api/cart/executions/${sessionId}`),
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

    browserLogin: () =>
      fetchJSON<CookieStatus>("/api/settings/cookies/login", {
        method: "POST",
        signal: AbortSignal.timeout(200000), // 200s — user logs in manually
      }),

    deleteCookies: () =>
      fetchJSON<{ message: string }>("/api/settings/cookies", {
        method: "DELETE",
      }),
  },
};
