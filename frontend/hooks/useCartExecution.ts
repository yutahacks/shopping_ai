"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { CartExecutionResult, CartStatusEvent } from "@/lib/types";

export function useCartExecution() {
  const [result, setResult] = useState<CartExecutionResult | null>(null);
  const [events, setEvents] = useState<CartStatusEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (sessionId: string, dryRun = false) => {
    setLoading(true);
    setError(null);
    setEvents([]);

    try {
      const initial = await api.cart.execute({ session_id: sessionId, dry_run: dryRun });
      setResult(initial);

      const eventSource = api.cart.streamStatus(initial.execution_id);

      eventSource.onmessage = (e: MessageEvent) => {
        const event: CartStatusEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);

        if (event.event_type === "completed" || event.event_type === "error") {
          eventSource.close();
          setLoading(false);
          // Update final result from the last event
          setResult((prev) =>
            prev
              ? {
                  ...prev,
                  status: event.event_type === "completed" ? "completed" : "failed",
                }
              : prev
          );
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setLoading(false);
        setError("ステータスの取得に失敗しました");
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : "実行に失敗しました";
      setError(message);
      setLoading(false);
    }
  }, []);

  return { result, events, loading, error, execute };
}
