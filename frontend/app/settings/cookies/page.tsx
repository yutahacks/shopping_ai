"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { CookieStatus } from "@/lib/types";

export default function CookiesPage() {
  const [status, setStatus] = useState<CookieStatus | null>(null);
  const [cookieJson, setCookieJson] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.settings.getCookieStatus().then(setStatus);
  }, []);

  const handleUpload = async () => {
    setLoading(true);
    try {
      const cookies = JSON.parse(cookieJson);
      if (!Array.isArray(cookies)) throw new Error("配列形式で入力してください");
      const newStatus = await api.settings.uploadCookies(cookies);
      setStatus(newStatus);
      setCookieJson("");
      toast.success("Cookieをアップロードしました");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "アップロードに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Cookieを削除しますか？")) return;
    await api.settings.deleteCookies();
    setStatus({ has_cookies: false, cookie_count: 0, is_valid: false, message: "削除しました" });
    toast.success("Cookieを削除しました");
  };

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/settings" className="text-muted-foreground hover:text-foreground">← 戻る</Link>
        <h1 className="text-xl font-bold">Cookie管理</h1>
      </div>

      {status && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              現在の状態
              {status.is_valid
                ? <Badge className="bg-green-100 text-green-800">有効</Badge>
                : <Badge variant="destructive">無効</Badge>
              }
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>{status.message}</p>
            {status.cookie_count > 0 && <p>{status.cookie_count}件のCookie</p>}
            {status.last_updated && (
              <p className="text-muted-foreground">
                最終更新: {new Date(status.last_updated).toLocaleString("ja-JP")}
              </p>
            )}
            {status.has_cookies && (
              <Button variant="destructive" size="sm" onClick={handleDelete}>
                Cookieを削除
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cookie JSONをアップロード</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            ブラウザ拡張機能（例: EditThisCookie）でエクスポートしたAmazon.co.jpの
            Cookie JSONを貼り付けてください。
          </p>
          <Textarea
            placeholder='[{"name": "session-id", "value": "...", "domain": ".amazon.co.jp", ...}]'
            value={cookieJson}
            onChange={(e) => setCookieJson(e.target.value)}
            rows={8}
            className="font-mono text-xs"
          />
          <Button
            onClick={handleUpload}
            disabled={loading || !cookieJson.trim()}
            className="w-full"
          >
            {loading ? "アップロード中..." : "アップロード"}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
