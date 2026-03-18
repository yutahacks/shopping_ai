"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import type { ShoppingPlan } from "@/lib/types";

interface PlanCardProps {
  plan: ShoppingPlan;
}

export function PlanCard({ plan }: PlanCardProps) {
  const router = useRouter();
  const activeItems = plan.items.filter((i) => !i.excluded);
  const excludedItems = plan.items.filter((i) => i.excluded);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          買い物リスト ({activeItems.length}件)
        </CardTitle>
        <p className="text-sm text-muted-foreground">{plan.reasoning}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {activeItems.map((item, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <span className="font-medium">{item.name}</span>
                <span className="ml-2 text-sm text-muted-foreground">{item.quantity}</span>
                {item.notes && (
                  <p className="text-xs text-blue-600">{item.notes}</p>
                )}
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
            <p className="text-sm font-medium text-muted-foreground mb-2">除外された商品:</p>
            <div className="space-y-1">
              {excludedItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <Badge variant="secondary">{item.name}</Badge>
                  {item.exclusion_reason && (
                    <span className="text-xs text-muted-foreground">{item.exclusion_reason}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {plan.rules_applied.length > 0 && (
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">適用ルール:</p>
            <ul className="text-xs text-muted-foreground space-y-1">
              {plan.rules_applied.map((rule, idx) => (
                <li key={idx}>• {rule}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
      <CardFooter>
        <Button
          className="w-full"
          onClick={() => router.push(`/plan/${plan.session_id}`)}
        >
          カートに追加する →
        </Button>
      </CardFooter>
    </Card>
  );
}
