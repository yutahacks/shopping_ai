import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/" className="text-muted-foreground hover:text-foreground">← 戻る</Link>
        <h1 className="text-xl font-bold">設定</h1>
      </div>

      <div className="grid gap-4">
        <Link href="/settings/cookies">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <CardTitle className="text-base">🍪 Cookie管理</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Amazon セッションCookieのアップロードと管理
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/settings/rules">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <CardTitle className="text-base">📋 ショッピングルール</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                除外食材、ブランド設定、価格戦略の編集
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </main>
  );
}
