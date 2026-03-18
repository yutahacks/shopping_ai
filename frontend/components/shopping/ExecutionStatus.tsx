"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CartExecutionResult, CartStatusEvent } from "@/lib/types";

interface ExecutionStatusProps {
  result: CartExecutionResult | null;
  events: CartStatusEvent[];
  loading: boolean;
}

const statusBadge = (status: string) => {
  switch (status) {
    case "added": return <Badge className="bg-green-100 text-green-800">追加済み</Badge>;
    case "not_found": return <Badge variant="outline">見つからず</Badge>;
    case "skipped": return <Badge variant="secondary">スキップ</Badge>;
    case "error": return <Badge variant="destructive">エラー</Badge>;
    default: return <Badge>{status}</Badge>;
  }
};

export function ExecutionStatus({ result, events, loading }: ExecutionStatusProps) {
  if (!result) return null;

  const progress = result.total_items > 0
    ? Math.round((result.items.length / result.total_items) * 100)
    : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>実行状況</span>
          {loading && (
            <span className="text-sm font-normal text-muted-foreground animate-pulse">
              処理中...
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>{result.items.length} / {result.total_items} 件処理</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-primary rounded-full h-2 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Summary */}
        {result.status === "completed" && (
          <div className="flex gap-4 text-sm">
            <span className="text-green-600">✓ 追加: {result.added_count}</span>
            <span className="text-red-600">✗ 失敗: {result.failed_count}</span>
            <span className="text-muted-foreground">スキップ: {result.skipped_count}</span>
          </div>
        )}

        {/* Item results */}
        <div className="space-y-2">
          {result.items.map((item, idx) => (
            <div key={idx} className="flex items-center justify-between py-1 border-b last:border-0">
              <div>
                <span className="text-sm font-medium">{item.item_name}</span>
                {item.product_found && item.product_found !== item.item_name && (
                  <p className="text-xs text-muted-foreground">{item.product_found}</p>
                )}
                {item.error_message && (
                  <p className="text-xs text-red-500">{item.error_message}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {item.price && (
                  <span className="text-xs text-muted-foreground">¥{item.price.toLocaleString()}</span>
                )}
                {statusBadge(item.status)}
              </div>
            </div>
          ))}
        </div>

        {result.error_message && (
          <p className="text-sm text-red-500">{result.error_message}</p>
        )}
      </CardContent>
    </Card>
  );
}
