"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { ShoppingInput } from "@/components/shopping/ShoppingInput";
import { PlanCard } from "@/components/shopping/PlanCard";
import { useShoppingPlan } from "@/hooks/useShoppingPlan";

export default function HomePage() {
  const router = useRouter();
  const { plan, loading, error, createPlan } = useShoppingPlan();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Check if setup has been completed
    const setupDone = localStorage.getItem("setup_completed");
    if (!setupDone) {
      router.replace("/setup");
      return;
    }
    setReady(true);
  }, [router]);

  const handleSubmit = async (request: string, context?: string) => {
    const result = await createPlan({ request, context });
    if (!result) {
      toast.error("プランの生成に失敗しました");
    }
  };

  if (!ready) {
    return null;
  }

  return (
    <main className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl sm:text-2xl font-bold">Amazon Fresh 買い物アシスタント</h1>
        <nav className="flex gap-4 text-sm">
          <Link href="/history" className="text-muted-foreground hover:text-foreground">
            履歴
          </Link>
          <Link href="/settings" className="text-muted-foreground hover:text-foreground">
            設定
          </Link>
        </nav>
      </div>

      <ShoppingInput onSubmit={handleSubmit} loading={loading} />

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
          {error}
        </div>
      )}

      {plan && <PlanCard plan={plan} />}
    </main>
  );
}
