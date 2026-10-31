// Mirrors backend/app/schemas.py. Keep the two in step.

export const CATEGORIES = ["hoodie", "t-shirt", "sweatshirt", "sweatpants"] as const;
export const SIZES = ["XS", "S", "M", "L", "XL", "XXL"] as const;
export const STATUSES = ["draft", "production", "launched", "closed"] as const;
export const CHANNELS = ["store", "online", "instagram", "event", "other"] as const;

export type Category = (typeof CATEGORIES)[number];
export type Size = (typeof SIZES)[number];
export type Status = (typeof STATUSES)[number];
export type Channel = (typeof CHANNELS)[number];

export interface Profile {
  name: string;
  one_liner: string;
  concepts: string;
  price_position: string;
  customer: string;
  never_do: string;
  currency: string;
  target_margin: number;
  min_margin: number;
  market_position: number;
  first_drop_units: number;
  min_order_qty: number;
}

export interface DnaRule { id: number; text: string; source: string; active: boolean; created_at: string }
export interface Signal { id: number; title: string; source: string; note: string; url: string; created_at: string }
export interface Colour { name: string; hex: string }

export interface TrendIdea {
  name: string;
  fit: number;
  lifespan: "micro" | "season" | "long";
  why: string;
  our_take: string;
  colours: Colour[];
  search_terms: string[];
  avoid: string;
}
export interface TrendReport {
  id: number;
  launch_month: string;
  hint: string;
  result: { trends: TrendIdea[]; summary: string };
  created_at: string;
}

export interface PieceIn {
  category: Category;
  name: string;
  color: string;
  fit: string;
  fabric: string;
  gsm: number | null;
  unit_cost: number | null;
  price: number | null;
  units_made: number | null;
  made_by_size: Partial<Record<Size, number>>;
}
export interface Piece extends PieceIn { id: number; look_id: number }

export interface StoreMood { lighting: string; scent: string; sound: string; display: string; ritual: string }

export interface LookIn { position: number; name: string; signature_detail: string; pieces: PieceIn[] }
export interface Look { id: number; position: number; name: string; signature_detail: string; pieces: Piece[] }

export interface DropIn {
  name: string;
  trend: string;
  launch_month: string;
  story: string;
  palette: Colour[];
  store: StoreMood;
  moodboard: string[];
  avoid: string[];
  looks: LookIn[];
}

export interface Expense { id: number; drop_id: number; label: string; amount: number; spent_on: string | null }

export interface Drop extends Omit<DropIn, "looks"> {
  id: number;
  status: Status;
  launched_on: string | null;
  created_at: string;
  looks: Look[];
  expenses: Expense[];
}

export interface DropSummary {
  id: number;
  name: string;
  trend: string;
  launch_month: string;
  status: Status;
  launched_on: string | null;
  created_at: string;
  revenue: number;
  units_sold: number;
  sell_through: number | null;
  net_profit: number;
}

export interface Sale {
  id: number;
  piece_id: number;
  quantity: number;
  unit_price: number;
  size: Size | null;
  sold_on: string;
  channel: Channel;
  note: string;
  piece_name: string;
  drop_id: number | null;
  drop_name: string;
}

export interface PieceMoney {
  id: number;
  name: string;
  category: Category;
  unit_cost: number | null;
  price: number | null;
  units_made: number | null;
  units_sold: number;
  units_left: number | null;
  sell_through: number | null;
  revenue: number;
  cost_of_sold: number | null;
  gross_profit: number | null;
  gross_margin: number | null;
  avg_selling_price: number | null;
  discount_rate: number | null;
  stock_value_at_cost: number | null;
  production_spend: number | null;
  oversold: boolean;
  sold_by_size: Partial<Record<Size, number>>;
}

export interface MonthPoint { month: string; revenue: number; units: number }

export interface DropMoney {
  currency: string;
  revenue: number;
  units_sold: number;
  units_made: number;
  sell_through: number | null;
  cost_of_sold: number;
  gross_profit: number;
  gross_margin: number | null;
  expenses: number;
  net_profit: number;
  production_spend: number;
  cash_back: number;
  payback: number | null;
  stock_value_at_cost: number;
  break_even_units_left: number | null;
  missing_costs: string[];
  pieces: PieceMoney[];
  by_month: MonthPoint[];
}

export interface SummaryDrop {
  id: number;
  name: string;
  status: Status;
  launch_month: string;
  revenue: number;
  units_sold: number;
  units_made: number;
  sell_through: number | null;
  gross_profit: number;
  gross_margin: number | null;
  expenses: number;
  net_profit: number;
  production_spend: number;
  cash_back: number;
  payback: number | null;
  stock_value_at_cost: number;
  break_even_units_left: number | null;
  missing_costs: string[];
  best_seller: string | null;
}

export interface MoneySummary {
  currency: string;
  totals: {
    revenue: number;
    gross_profit: number;
    gross_margin: number | null;
    net_profit: number;
    expenses: number;
    production_spend: number;
    cash_back: number;
    stock_value_at_cost: number;
    units_sold: number;
  };
  drops: SummaryDrop[];
  by_month: MonthPoint[];
  by_channel: Record<string, number>;
}

export interface Competitor { id: number; brand: string; category: Category; price: number; note: string }

export interface PriceSuggestion {
  currency: string;
  recommended: number;
  floor: number;
  cost_target: number;
  market_low: number | null;
  market_median: number | null;
  market_high: number | null;
  margin_at_recommended: number;
  markup: number;
  reasons: string[];
  warnings: string[];
  current_margin: number | null;
}

export interface PiecePricing {
  piece_id: number;
  look: number;
  name: string;
  category: Category;
  unit_cost: number | null;
  price: number | null;
  suggestion?: PriceSuggestion;
}

export interface CategoryPlan {
  category: Category;
  units_per_piece: number;
  sell_through: number | null;
  reason: string;
  by_size: Partial<Record<Size, number>>;
  below_moq: boolean;
}

export interface StockPlan {
  currency: string;
  min_order_qty: number;
  first_drop: boolean;
  based_on: string[];
  size_curve: Record<Size, number>;
  size_data_weight: number;
  categories: CategoryPlan[];
  drop?: {
    id: number;
    name: string;
    total_units: number;
    cash_needed: number;
    missing_costs: string[];
    pieces: {
      piece_id: number;
      look: number;
      name: string;
      category: Category;
      units: number;
      by_size: Partial<Record<Size, number>>;
      unit_cost: number | null;
      cash_needed: number | null;
      current_units: number | null;
      below_moq: boolean;
    }[];
  };
}

export interface DesignFeedback {
  summary: string;
  scores: { brand_fit: number; trend: number; effortless: number; wearability: number };
  works: string[];
  change: string[];
  dna_takeaways: string[];
}
export interface Design {
  id: number;
  title: string;
  drop_id: number | null;
  note: string;
  feedback: DesignFeedback;
  created_at: string;
  image_url: string;
}

export interface AppConfig { auth_required: boolean; ai_enabled: boolean; model: string }
