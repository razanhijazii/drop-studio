import type {
  AppConfig, Competitor, DnaRule, Drop, DropIn, DropMoney, DropSummary, Design, Expense, Look, LookIn,
  MoneySummary, Piece, PieceIn, PiecePricing, PriceSuggestion, Profile, Sale, Signal, StockPlan, TrendReport,
  Category, Channel, Size, Status, StoreMood, Colour,
} from "./types";

declare const __API_URL__: string;
export const API_URL = __API_URL__;

const TOKEN_KEY = "drop-studio-token";

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(t: string | null) {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ }
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

let onUnauthorized: () => void = () => {};
export function handleUnauthorized(fn: () => void) { onUnauthorized = fn; }

function detail(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0]?.msg) {
      const loc = Array.isArray(d[0].loc) ? d[0].loc.filter((x: unknown) => x !== "body").join(" → ") : "";
      return `${loc ? loc + ": " : ""}${d[0].msg}`;
    }
  }
  if (status >= 500) return "The server had a problem. Try again in a moment.";
  return `Request failed (${status}).`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(API_URL + path, { method, headers, body: payload });
  } catch {
    throw new ApiError("Can't reach the server. If it was asleep, it can take up to a minute to wake up.", 0);
  }
  if (res.status === 401 && path !== "/auth/login") {
    setToken(null);
    onUnauthorized();
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(detail(data, res.status), res.status);
  return data as T;
}

const get = <T>(p: string) => request<T>("GET", p);
const post = <T>(p: string, b?: unknown) => request<T>("POST", p, b);
const put = <T>(p: string, b?: unknown) => request<T>("PUT", p, b);
const patch = <T>(p: string, b?: unknown) => request<T>("PATCH", p, b);
const del = (p: string) => request<void>("DELETE", p);

export async function imageUrl(path: string): Promise<string> {
  const res = await fetch(API_URL + path, { headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {} });
  if (!res.ok) throw new ApiError("Image unavailable", res.status);
  return URL.createObjectURL(await res.blob());
}

export type PieceUpdate = Partial<PieceIn>;
export interface SaleIn {
  piece_id: number; quantity: number; unit_price?: number | null; size?: Size | null;
  sold_on?: string; channel?: Channel; note?: string;
}
export interface DropUpdate {
  name?: string; trend?: string; launch_month?: string; story?: string; palette?: Colour[];
  store?: StoreMood; moodboard?: string[]; avoid?: string[]; status?: Status; launched_on?: string | null;
}

export const api = {
  config: () => get<AppConfig>("/config"),
  login: (password: string) => post<{ token: string; expires_at: string }>("/auth/login", { password }),

  profile: () => get<Profile>("/brand/profile"),
  saveProfile: (p: Profile) => put<Profile>("/brand/profile", p),
  dna: () => get<DnaRule[]>("/brand/dna"),
  addDna: (items: { text: string; source?: string }[]) => post<DnaRule[]>("/brand/dna", items),
  updateDna: (id: number, r: { text: string; source: string; active: boolean }) => patch<DnaRule>(`/brand/dna/${id}`, r),
  deleteDna: (id: number) => del(`/brand/dna/${id}`),

  signals: () => get<Signal[]>("/trends/signals"),
  addSignal: (s: { title: string; source: string; note: string; url: string }) => post<Signal>("/trends/signals", s),
  deleteSignal: (id: number) => del(`/trends/signals/${id}`),
  scout: (launch_month: string, hint: string) => post<TrendReport>("/trends/scout", { launch_month, hint }),
  reports: () => get<TrendReport[]>("/trends/reports"),

  drops: () => get<DropSummary[]>("/drops"),
  drop: (id: number) => get<Drop>(`/drops/${id}`),
  createDrop: (d: DropIn) => post<Drop>("/drops", d),
  generateDrop: (trend: string, launch_month: string, direction: string) =>
    post<DropIn>("/drops/generate", { trend, launch_month, direction }),
  updateDrop: (id: number, d: DropUpdate) => patch<Drop>(`/drops/${id}`, d),
  deleteDrop: (id: number) => del(`/drops/${id}`),
  addLook: (dropId: number, l: LookIn) => post<Look>(`/drops/${dropId}/looks`, l),
  updateLook: (id: number, l: { name?: string; signature_detail?: string }) => patch<Look>(`/drops/looks/${id}`, l),
  deleteLook: (id: number) => del(`/drops/looks/${id}`),
  addPiece: (lookId: number, p: PieceIn) => post<Piece>(`/drops/looks/${lookId}/pieces`, p),
  updatePiece: (id: number, p: PieceUpdate) => patch<Piece>(`/drops/pieces/${id}`, p),
  deletePiece: (id: number) => del(`/drops/pieces/${id}`),
  addExpense: (dropId: number, e: { label: string; amount: number; spent_on?: string | null }) =>
    post<Expense>(`/drops/${dropId}/expenses`, e),
  deleteExpense: (id: number) => del(`/drops/expenses/${id}`),

  sales: (dropId?: number) => get<Sale[]>(`/sales${dropId ? `?drop_id=${dropId}` : ""}`),
  recordSales: (items: SaleIn[]) => post<Sale[]>("/sales", items),
  deleteSale: (id: number) => del(`/sales/${id}`),

  summary: () => get<MoneySummary>("/money/summary"),
  dropMoney: (id: number) => get<DropMoney>(`/money/drops/${id}`),

  competitors: () => get<Competitor[]>("/pricing/competitors"),
  addCompetitor: (c: { brand: string; category: Category; price: number; note: string }) =>
    post<Competitor>("/pricing/competitors", c),
  deleteCompetitor: (id: number) => del(`/pricing/competitors/${id}`),
  suggestPrice: (unit_cost: number, category: Category, current_price?: number | null) =>
    post<PriceSuggestion>("/pricing/suggest", { unit_cost, category, current_price: current_price || null }),
  dropPricing: (id: number) => get<PiecePricing[]>(`/pricing/drops/${id}`),

  stockPlan: (dropId?: number) => get<StockPlan>(`/stock/plan${dropId ? `?drop_id=${dropId}` : ""}`),

  designs: () => get<Design[]>("/designs"),
  reviewDesign: (form: FormData) => post<Design>("/designs/review", form),
  deleteDesign: (id: number) => del(`/designs/${id}`),
};
