"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ShoppingInputProps {
  onSubmit: (request: string, context?: string) => void;
  loading?: boolean;
}

export function ShoppingInput({ onSubmit, loading }: ShoppingInputProps) {
  const [request, setRequest] = useState("");
  const [context, setContext] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!request.trim()) return;
    onSubmit(request.trim(), context.trim() || undefined);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>何を買いますか？</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="request">リクエスト</Label>
            <Textarea
              id="request"
              placeholder="例：カレーを4人分作りたい、今週の晩ご飯の食材"
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              rows={3}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="context">追加情報（任意）</Label>
            <Input
              id="context"
              placeholder="例：予算3000円以内、子供が嫌いな食材は除く"
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={loading || !request.trim()} className="w-full">
            {loading ? "プランを生成中..." : "買い物リストを生成"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
