"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRules } from "@/hooks/useRules";
import type { AvoidRule, BrandRule, ShoppingRules } from "@/lib/types";

export default function RulesPage() {
  const { rules, loading, saving, saveRules } = useRules();

  if (loading) {
    return <div className="max-w-2xl mx-auto p-6">読み込み中...</div>;
  }

  if (!rules) {
    return <div className="max-w-2xl mx-auto p-6">ルールの読み込みに失敗しました</div>;
  }

  return <RulesEditor rules={rules} saving={saving} onSave={saveRules} />;
}

function RulesEditor({
  rules,
  saving,
  onSave,
}: {
  rules: ShoppingRules;
  saving: boolean;
  onSave: (rules: ShoppingRules) => Promise<ShoppingRules | null>;
}) {
  const [draft, setDraft] = useState<ShoppingRules>(rules);
  const [newAvoid, setNewAvoid] = useState<Omit<AvoidRule, "reason">>({ item_pattern: "", override_keyword: "" });
  const [newBrand, setNewBrand] = useState<BrandRule>({ product_pattern: "", brand: "", reason: "" });

  const handleSave = async () => {
    const result = await onSave(draft);
    if (result) toast.success("ルールを保存しました");
    else toast.error("保存に失敗しました");
  };

  const addAvoidRule = () => {
    if (!newAvoid.item_pattern.trim()) return;
    setDraft((d) => ({ ...d, avoid: [...d.avoid, { ...newAvoid }] }));
    setNewAvoid({ item_pattern: "", override_keyword: "" });
  };

  const removeAvoidRule = (idx: number) => {
    setDraft((d) => ({ ...d, avoid: d.avoid.filter((_, i) => i !== idx) }));
  };

  const addBrandRule = () => {
    if (!newBrand.product_pattern.trim() || !newBrand.brand.trim()) return;
    setDraft((d) => ({ ...d, brands: [...d.brands, { ...newBrand }] }));
    setNewBrand({ product_pattern: "", brand: "", reason: "" });
  };

  const removeBrandRule = (idx: number) => {
    setDraft((d) => ({ ...d, brands: d.brands.filter((_, i) => i !== idx) }));
  };

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings" className="text-muted-foreground hover:text-foreground">← 戻る</Link>
          <h1 className="text-xl font-bold">ショッピングルール</h1>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "保存"}
        </Button>
      </div>

      {/* Avoid rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">除外リスト</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {draft.avoid.map((rule, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <Badge variant="outline">{rule.item_pattern}</Badge>
                {rule.override_keyword && (
                  <span className="text-xs text-muted-foreground">
                    「{rule.override_keyword}」の場合は除外しない
                  </span>
                )}
                <button
                  onClick={() => removeAvoidRule(idx)}
                  className="ml-auto text-destructive text-sm"
                >
                  削除
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="食材・商品名"
              value={newAvoid.item_pattern}
              onChange={(e) => setNewAvoid((p) => ({ ...p, item_pattern: e.target.value }))}
              className="flex-1"
            />
            <Input
              placeholder="例外キーワード（任意）"
              value={newAvoid.override_keyword || ""}
              onChange={(e) => setNewAvoid((p) => ({ ...p, override_keyword: e.target.value }))}
              className="flex-1"
            />
            <Button variant="outline" onClick={addAvoidRule}>追加</Button>
          </div>
        </CardContent>
      </Card>

      {/* Brand rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">ブランド設定</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {draft.brands.map((rule, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="text-sm">{rule.product_pattern}</span>
                <span className="text-muted-foreground">→</span>
                <Badge>{rule.brand}</Badge>
                <button
                  onClick={() => removeBrandRule(idx)}
                  className="ml-auto text-destructive text-sm"
                >
                  削除
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="商品カテゴリ"
              value={newBrand.product_pattern}
              onChange={(e) => setNewBrand((p) => ({ ...p, product_pattern: e.target.value }))}
              className="flex-1"
            />
            <Input
              placeholder="ブランド名"
              value={newBrand.brand}
              onChange={(e) => setNewBrand((p) => ({ ...p, brand: e.target.value }))}
              className="flex-1"
            />
            <Button variant="outline" onClick={addBrandRule}>追加</Button>
          </div>
        </CardContent>
      </Card>

      {/* Price strategy */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">価格設定</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>価格戦略</Label>
            <div className="flex gap-2">
              {(["cheapest", "value", "premium"] as const).map((s) => (
                <Button
                  key={s}
                  variant={draft.price.strategy === s ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDraft((d) => ({ ...d, price: { ...d.price, strategy: s } }))}
                >
                  {s === "cheapest" ? "最安値" : s === "value" ? "コスパ" : "プレミアム"}
                </Button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <Label>1商品の上限価格（円）</Label>
            <Input
              type="number"
              placeholder="上限なし"
              value={draft.price.max_price_per_item ?? ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  price: {
                    ...d.price,
                    max_price_per_item: e.target.value ? Number(e.target.value) : undefined,
                  },
                }))
              }
              className="w-40"
            />
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">AIへのメモ</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="例：有機野菜を優先してください。なるべく国産を選んでください。"
            value={draft.notes ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value || undefined }))}
            rows={4}
          />
        </CardContent>
      </Card>
    </main>
  );
}
