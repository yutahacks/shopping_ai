"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { PlanRequest, ShoppingPlan } from "@/lib/types";

export function useShoppingPlan() {
  const [plan, setPlan] = useState<ShoppingPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPlan = async (request: PlanRequest) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.shopping.createPlan(request);
      setPlan(result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "プランの生成に失敗しました";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { plan, setPlan, loading, error, createPlan };
}
