// Shopping
export interface PlanRequest {
  request: string;
  context?: string;
}

export interface ShoppingItem {
  name: string;
  quantity: string;
  estimated_price?: number;
  excluded: boolean;
  exclusion_reason?: string;
  substitution?: string;
  notes?: string;
}

export interface ShoppingPlan {
  session_id: string;
  user_request: string;
  context?: string;
  items: ShoppingItem[];
  reasoning: string;
  rules_applied: string[];
}

export interface ShoppingSession {
  session_id: string;
  user_request: string;
  context?: string;
  created_at: string;
  item_count: number;
  executed: boolean;
}

// Cart
export interface CartExecutionRequest {
  session_id: string;
  dry_run?: boolean;
}

export type CartItemStatus = "added" | "not_found" | "skipped" | "error";
export type CartExecutionStatus = "pending" | "running" | "completed" | "failed";

export interface CartItemResult {
  item_name: string;
  status: CartItemStatus;
  product_found?: string;
  price?: number;
  asin?: string;
  error_message?: string;
}

export interface CartExecutionResult {
  execution_id: string;
  session_id: string;
  status: CartExecutionStatus;
  items: CartItemResult[];
  total_items: number;
  added_count: number;
  failed_count: number;
  skipped_count: number;
  error_message?: string;
}

export type CartStatusEventType = "started" | "item_processed" | "completed" | "error";

export interface CartStatusEvent {
  execution_id: string;
  event_type: CartStatusEventType;
  current_item?: string;
  item_result?: CartItemResult;
  progress: number;
  total: number;
  message?: string;
}

// Rules
export interface AvoidRule {
  item_pattern: string;
  reason?: string;
  override_keyword?: string;
}

export interface BrandRule {
  product_pattern: string;
  brand: string;
  reason?: string;
}

export type PriceStrategy = "cheapest" | "value" | "premium";

export interface PricePreference {
  strategy: PriceStrategy;
  max_price_per_item?: number;
}

export interface ShoppingRules {
  avoid: AvoidRule[];
  brands: BrandRule[];
  price: PricePreference;
  notes?: string;
}

// Settings
export interface CookieEntry {
  name: string;
  value: string;
  domain: string;
  path: string;
  secure: boolean;
  http_only: boolean;
  same_site?: string;
  expires?: number;
}

export interface CookieStatus {
  has_cookies: boolean;
  cookie_count: number;
  is_valid: boolean;
  last_updated?: string;
  message: string;
}
