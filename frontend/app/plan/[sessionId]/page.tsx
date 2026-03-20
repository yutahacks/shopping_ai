"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExecutionStatus } from "@/components/shopping/ExecutionStatus";
import { useCartExecution } from "@/hooks/useCartExecution";
import { api } from "@/lib/api";
import type { ShoppingPlan, ShoppingItem } from "@/lib/types";

export default function PlanPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [plan, setPlan] = useState<ShoppingPlan | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editItems, setEditItems] = useState<ShoppingItem[]>([]);
  const [saving, setSaving] = useState(false);
  const { result, events, loading: executing, error, execute } = useCartExecution();

  useEffect(() => {
    api.shopping.getSession(sessionId)
      .then((p) => {
        setPlan(p);
        setEditItems(p.items);
      })
      .catch(() => toast.error("プランの読み込みに失敗しました"))
      .finally(() => setLoadingPlan(false));
  }, [sessionId]);

  const handleExecute = async (dryRun = false) => {
    if (!dryRun) {
      const confirmed = window.confirm(
        "カートに追加を開始しますか？この操作はAmazon Freshのカートに商品を追加します。"
      );
      if (!confirmed) return;
    }
    await execute(sessionId, dryRun);
    if (!dryRun) {
      toast.success("カートへの追加を開始しました");
    }
  };

  const handleSaveEdits = useCallback(async () => {
    setSaving(true);
    try {
      const updated = await api.shopping.updateItems(sessionId, editItems);
      setPlan(updated);
      setEditItems(updated.items);
      setEditing(false);
      toast.success("プランを更新しました");
    } catch {
      toast.error("更新に失敗しました");
    } finally {
      setSaving(false);
    }
  }, [sessionId, editItems]);

  const updateEditItem = (index: number, field: keyof ShoppingItem, value: string | number | boolean | undefined) => {
    setEditItems((items) =>
      items.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const removeEditItem = (index: number) => {
    setEditItems((items) => items.filter((_, i) => i !== index));
  };

  const addEditItem = () => {
    setEditItems((items) => [
      ...items,
      { name: "", quantity: "1個", excluded: false },
    ]);
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
  const estimatedTotal = activeItems.reduce((sum, item) => sum + (item.estimated_price ?? 0), 0);

  return (
    <main className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="text-muted-foreground hover:text-foreground">
          ← 戻る
        </button>
        <h1 className="text-xl font-bold">買い物プランの確認</h1>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">リクエスト: {plan.user_request}</CardTitle>
            {!result && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (editing) {
                    setEditItems(plan.items);
                  }
                  setEditing(!editing);
                }}
              >
                {editing ? "キャンセル" : "編集"}
              </Button>
            )}
          </div>
          {plan.context && (
            <p className="text-sm text-muted-foreground">{plan.context}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {editing ? (
            /* Edit mode */
            <div className="space-y-3">
              <p className="text-sm font-medium">アイテムを編集 ({editItems.length}件)</p>
              {editItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 py-2 border-b last:border-0">
                  <Input
                    value={item.name}
                    onChange={(e) => updateEditItem(idx, "name", e.target.value)}
                    placeholder="商品名"
                    className="flex-1"
                  />
                  <Input
                    value={item.quantity}
                    onChange={(e) => updateEditItem(idx, "quantity", e.target.value)}
                    placeholder="数量"
                    className="w-20"
                  />
                  <Input
                    type="number"
                    value={item.estimated_price ?? ""}
                    onChange={(e) =>
                      updateEditItem(idx, "estimated_price", e.target.value ? Number(e.target.value) : undefined)
                    }
                    placeholder="価格"
                    className="w-24"
                  />
                  <button
                    onClick={() => removeEditItem(idx)}
                    className="text-destructive text-sm shrink-0"
                  >
                    削除
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={addEditItem} className="flex-1">
                  + アイテム追加
                </Button>
                <Button size="sm" onClick={handleSaveEdits} disabled={saving} className="flex-1">
                  {saving ? "保存中..." : "保存"}
                </Button>
              </div>
            </div>
          ) : (
            /* View mode */
            <>
              <div className="space-y-2">
                <p className="text-sm font-medium">カートに追加する商品 ({activeItems.length}件)</p>
                {activeItems.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="min-w-0 flex-1">
                      <span className="font-medium">{item.name}</span>
                      <span className="ml-2 text-sm text-muted-foreground">{item.quantity}</span>
                      {item.notes && <p className="text-xs text-blue-600">{item.notes}</p>}
                    </div>
                    {item.estimated_price != null && (
                      <span className="text-sm text-muted-foreground shrink-0 ml-2">
                        約¥{item.estimated_price.toLocaleString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {estimatedTotal > 0 && (
                <div className="flex justify-end pt-2 border-t">
                  <span className="font-semibold text-base">
                    合計（概算）: ¥{estimatedTotal.toLocaleString()}
                  </span>
                </div>
              )}

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
            </>
          )}
        </CardContent>
      </Card>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
          {error}
        </div>
      )}

      {!result && !editing && (
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
