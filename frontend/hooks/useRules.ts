"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { ShoppingRules } from "@/lib/types";

export function useRules() {
  const [rules, setRules] = useState<ShoppingRules | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.rules.get()
      .then(setRules)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const saveRules = async (updated: ShoppingRules) => {
    setSaving(true);
    setError(null);
    try {
      const saved = await api.rules.update(updated);
      setRules(saved);
      return saved;
    } catch (err) {
      const message = err instanceof Error ? err.message : "保存に失敗しました";
      setError(message);
      return null;
    } finally {
      setSaving(false);
    }
  };

  return { rules, setRules, loading, saving, error, saveRules };
}
