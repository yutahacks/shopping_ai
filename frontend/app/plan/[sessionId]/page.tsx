"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExecutionStatus } from "@/components/shopping/ExecutionStatus";
import { useCartExecution } from "@/hooks/useCartExecution";
import { api } from "@/lib/api";
import type { ShoppingPlan } from "@/lib/types";

export default function PlanPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [plan, setPlan] = useState<ShoppingPlan | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(true);
  const { result, events, loading: executing, error, execute } = useCartExecution();

  useEffect(() => {
    api.shopping.getSession(sessionId)
      .then(setPlan)
      .catch(() => toast.error("プランの読み込みに失敗しました"))
      .finally(() => setLoadingPlan(false));
  }, [sessionId]);

  const handleExecute = async (dryRun = false) => {
    await execute(sessionId, dryRun);
    if (!dryRun) {
      toast.success("カートへの追加を開始しました");
    }
  };

  if (loadingPlan) {
    return <div className="max-w-2xl mx-auto p-6">読み込み中...</div>;
  }

  if (!plan) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <p>プランが見つかりません</p>
        <Link href="/" className="text-blue-600 hover:underline">トップに戻る</Link>
      </div>
    );
  }

  const activeItems = plan.items.filter((i) => !i.excluded);
  const excludedItems = plan.items.filter((i) => i.excluded);

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="text-muted-foreground hover:text-foreground">
          ← 戻る
        </button>
        <h1 className="text-xl font-bold">買い物プランの確認</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">リクエスト: {plan.user_request}</CardTitle>
          {plan.context && (
            <p className="text-sm text-muted-foreground">{plan.context}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">カートに追加する商品 ({activeItems.length}件)</p>
            {activeItems.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <span className="font-medium">{item.name}</span>
                  <span className="ml-2 text-sm text-muted-foreground">{item.quantity}</span>
                  {item.notes && <p className="text-xs text-blue-600">{item.notes}</p>}
                </div>
                {item.estimated_price && (
                  <span className="text-sm text-muted-foreground">
                    約¥{item.estimated_price.toLocaleString()}
                  </span>
                )}
              </div>
            ))}
          </div>

          {excludedItems.length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">除外済み</p>
              <div className="flex flex-wrap gap-2">
                {excludedItems.map((item, idx) => (
                  <Badge key={idx} variant="secondary">
                    {item.name}
                    {item.exclusion_reason && ` (${item.exclusion_reason})`}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
          {error}
        </div>
      )}

      {!result && (
        <div className="flex gap-3">
          <Button
            className="flex-1"
            onClick={() => handleExecute(false)}
            disabled={executing || activeItems.length === 0}
          >
            {executing ? "実行中..." : "Amazon Fresh カートに追加"}
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExecute(true)}
            disabled={executing}
          >
            ドライラン
          </Button>
        </div>
      )}

      <p className="text-xs text-muted-foreground text-center">
        ※ このアプリはカートへの追加のみ行います。購入はAmazon Freshのページで行ってください。
      </p>

      <ExecutionStatus result={result} events={events} loading={executing} />
    </main>
  );
}
