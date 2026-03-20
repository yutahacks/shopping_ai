import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking
import { api } from "@/lib/api";

describe("API client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("createPlan sends POST with correct body", async () => {
    const mockPlan = {
      session_id: "test-123",
      user_request: "カレー4人分",
      items: [],
      reasoning: "テスト",
      rules_applied: [],
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPlan),
    });

    const result = await api.shopping.createPlan({ request: "カレー4人分" });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/shopping/plan");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ request: "カレー4人分" });
    expect(result.session_id).toBe("test-123");
  });

  it("listSessions sends GET with query params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await api.shopping.listSessions(10, 5);

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/shopping/sessions?limit=10&offset=5");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "Session not found" }),
    });

    await expect(api.shopping.getSession("bad-id")).rejects.toThrow("Session not found");
  });

  it("updateItems sends PUT with items array", async () => {
    const mockPlan = {
      session_id: "s-1",
      user_request: "test",
      items: [{ name: "牛肉", quantity: "300g", excluded: false }],
      reasoning: "",
      rules_applied: [],
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPlan),
    });

    await api.shopping.updateItems("s-1", [
      { name: "牛肉", quantity: "300g", excluded: false },
    ]);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/shopping/sessions/s-1/items");
    expect(options.method).toBe("PUT");
  });

  it("reuseSession sends POST with session_id", async () => {
    const mockPlan = {
      session_id: "new-123",
      user_request: "test",
      items: [],
      reasoning: "再利用",
      rules_applied: [],
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPlan),
    });

    const result = await api.shopping.reuseSession("old-123");

    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ session_id: "old-123" });
    expect(result.session_id).toBe("new-123");
  });

  it("cart.execute sends correct request", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          execution_id: "exec-1",
          session_id: "s-1",
          status: "pending",
          items: [],
          total_items: 3,
          added_count: 0,
          failed_count: 0,
          skipped_count: 0,
        }),
    });

    const result = await api.cart.execute({ session_id: "s-1", dry_run: true });
    expect(result.execution_id).toBe("exec-1");
  });
});
