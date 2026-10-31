let currency = "USD";
export const setCurrency = (c: string) => { currency = c || "USD"; };

export function money(n: number | null | undefined, opts: { cents?: boolean } = {}): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency", currency,
      minimumFractionDigits: opts.cents ? 2 : 0,
      maximumFractionDigits: opts.cents ? 2 : 0,
    }).format(n);
  } catch {
    return `${currency} ${n.toFixed(opts.cents ? 2 : 0)}`;
  }
}

export const pct = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined ? "–" : `${(n * 100).toFixed(digits)}%`;

export const num = (n: number | null | undefined) => (n === null || n === undefined ? "–" : n.toLocaleString());

export function monthLabel(ym: string): string {
  if (!/^\d{4}-\d{2}$/.test(ym)) return ym || "–";
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

export function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function monthsAhead(n: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** Parse a form value into a number or null ("" -> null). */
export const toNum = (v: string): number | null => (v.trim() === "" || Number.isNaN(Number(v)) ? null : Number(v));

export const searchLinks = (q: string) => {
  const u = encodeURIComponent(q);
  return [
    { label: "Pinterest", href: `https://www.pinterest.com/search/pins/?q=${u}` },
    { label: "TikTok", href: `https://www.tiktok.com/search?q=${u}` },
    { label: "Images", href: `https://www.google.com/search?tbm=isch&q=${u}` },
  ];
};
