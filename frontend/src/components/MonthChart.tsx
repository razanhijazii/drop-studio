import { useState } from "react";
import type { MonthPoint } from "../lib/types";
import { money, monthLabel } from "../lib/format";

/** Revenue by month as bars, with a hover/tap readout. Hand-drawn SVG, no chart library. */
export function MonthChart({ data }: { data: MonthPoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (!data.length) return null;

  const W = 640, H = 220, padL = 52, padR = 12, padT = 16, padB = 32;
  const max = Math.max(...data.map((d) => d.revenue), 1);
  const nice = niceMax(max);
  const ticks = [0, nice / 2, nice];
  const iw = W - padL - padR, ih = H - padT - padB;
  const bw = Math.min(48, (iw / data.length) * 0.62);
  const x = (i: number) => padL + (iw / data.length) * (i + 0.5);
  const y = (v: number) => padT + ih - (v / nice) * ih;
  const shown = hover ?? data.length - 1;
  const labelEvery = Math.ceil(data.length / 8);

  return (
    <figure className="chart">
      <figcaption className="chart-readout">
        <span className="eyebrow">{monthLabel(data[shown].month)}</span>
        <strong>{money(data[shown].revenue)}</strong>
        <span className="muted">{data[shown].units} units</span>
      </figcaption>
      <div className="chart-scroll">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Revenue by month" onMouseLeave={() => setHover(null)}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} className="grid" />
              <text x={padL - 8} y={y(t) + 4} textAnchor="end" className="tick">{compact(t)}</text>
            </g>
          ))}
          {data.map((d, i) => (
            <g key={d.month} onMouseEnter={() => setHover(i)} onClick={() => setHover(i)}>
              <rect x={x(i) - (iw / data.length) / 2} y={padT} width={iw / data.length} height={ih} fill="transparent" />
              <rect
                x={x(i) - bw / 2}
                y={y(d.revenue)}
                width={bw}
                height={Math.max(0, padT + ih - y(d.revenue))}
                rx={2}
                className={i === shown ? "bar on" : "bar"}
              />
              {i % labelEvery === 0 && (
                <text x={x(i)} y={H - 10} textAnchor="middle" className="tick">{shortMonth(d.month, i === 0)}</text>
              )}
            </g>
          ))}
        </svg>
      </div>
    </figure>
  );
}

function shortMonth(ym: string, first: boolean) {
  const [y, m] = ym.split("-").map(Number);
  const name = new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "short" });
  return first || m === 1 ? `${name} ’${String(y).slice(2)}` : name;
}

function niceMax(v: number) {
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  const f = v / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
}

function compact(v: number) {
  if (v >= 1000) return `${(v / 1000).toFixed(v % 1000 ? 1 : 0)}k`;
  return String(Math.round(v));
}
