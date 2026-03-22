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
        let event: CartStatusEvent;
        try {
          event = JSON.parse(e.data) as CartStatusEvent;
        } catch {
          console.error("Failed to parse SSE message:", e.data);
          return;
        }
        setEvents((prev) => [...prev, event]);

        if (event.event_type === "item_processed" && event.item_result) {
          const item = event.item_result;
          setResult((prev) => {
            if (!prev) return prev;
            const newItems = [...prev.items, item];
            return {
              ...prev,
              status: "running",
              items: newItems,
              added_count: prev.added_count + (item.status === "added" ? 1 : 0),
              failed_count: prev.failed_count + (item.status === "error" || item.status === "not_found" ? 1 : 0),
              skipped_count: prev.skipped_count + (item.status === "skipped" ? 1 : 0),
            };
          });
        }

        if (event.event_type === "completed" || event.event_type === "error") {
          eventSource.close();
          setLoading(false);
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
