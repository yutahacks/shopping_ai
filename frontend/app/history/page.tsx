"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ShoppingSession } from "@/lib/types";

export default function HistoryPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<ShoppingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [reusing, setReusing] = useState<string | null>(null);

  useEffect(() => {
    api.shopping.listSessions()
      .then(setSessions)
      .finally(() => setLoading(false));
  }, []);

  const handleReuse = async (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setReusing(sessionId);
    try {
      const newPlan = await api.shopping.reuseSession(sessionId);
      toast.success("プランを再利用しました");
      router.push(`/plan/${newPlan.session_id}`);
    } catch {
      toast.error("再利用に失敗しました");
    } finally {
      setReusing(null);
    }
  };

  if (loading) {
    return <div className="max-w-2xl mx-auto p-6">読み込み中...</div>;
  }

  return (
    <main className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/" className="text-muted-foreground hover:text-foreground">← 戻る</Link>
        <h1 className="text-xl font-bold">買い物履歴</h1>
      </div>

      {sessions.length === 0 ? (
        <p className="text-muted-foreground">履歴がありません</p>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <Link key={session.session_id} href={`/plan/${session.session_id}`}>
              <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
                <CardHeader className="py-3">
                  <CardTitle className="text-base flex items-center justify-between gap-2">
                    <span className="truncate">{session.user_request}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      {session.executed && (
                        <Badge className="bg-green-100 text-green-800">実行済み</Badge>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => handleReuse(session.session_id, e)}
                        disabled={reusing === session.session_id}
                      >
                        {reusing === session.session_id ? "..." : "再利用"}
                      </Button>
                    </div>
                  </CardTitle>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{session.item_count}件</span>
                    <span>{new Date(session.created_at).toLocaleDateString("ja-JP")}</span>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
