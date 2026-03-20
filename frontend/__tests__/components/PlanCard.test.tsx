import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PlanCard } from "@/components/shopping/PlanCard";
import type { ShoppingPlan } from "@/lib/types";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
  }),
}));

const mockPlan: ShoppingPlan = {
  session_id: "test-session-1",
  user_request: "カレーを4人分作りたい",
  items: [
    { name: "牛肉", quantity: "300g", estimated_price: 800, excluded: false },
    { name: "玉ねぎ", quantity: "2個", estimated_price: 100, excluded: false },
    { name: "カレールー", quantity: "1箱", estimated_price: 300, excluded: false },
    {
      name: "じゃがいも",
      quantity: "3個",
      estimated_price: 150,
      excluded: true,
      exclusion_reason: "avoidルール",
    },
  ],
  reasoning: "4人分のカレーに必要な食材をリストアップしました。",
  rules_applied: ["じゃがいもをavoidリストにより除外"],
};

describe("PlanCard", () => {
  it("renders active items count", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText(/買い物リスト \(3件\)/)).toBeTruthy();
  });

  it("renders active item names", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText("牛肉")).toBeTruthy();
    expect(screen.getByText("玉ねぎ")).toBeTruthy();
    expect(screen.getByText("カレールー")).toBeTruthy();
  });

  it("renders excluded items section", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText("除外された商品:")).toBeTruthy();
  });

  it("renders estimated total", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText(/¥1,200/)).toBeTruthy();
  });

  it("renders reasoning", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText(/4人分のカレーに必要な食材/)).toBeTruthy();
  });

  it("renders rules applied", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText(/じゃがいもをavoidリストにより除外/)).toBeTruthy();
  });

  it("renders cart button", () => {
    render(<PlanCard plan={mockPlan} />);
    expect(screen.getByText("カートに追加する →")).toBeTruthy();
  });
});
