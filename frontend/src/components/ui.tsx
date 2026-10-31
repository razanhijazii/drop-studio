import { useState, type ReactNode, type InputHTMLAttributes, type TextareaHTMLAttributes, type SelectHTMLAttributes } from "react";
import type { Colour } from "../lib/types";
import { searchLinks } from "../lib/format";

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "quiet";
  size?: "md" | "sm";
  busy?: boolean;
};

export function Button({ variant = "primary", size = "md", busy, children, disabled, className = "", ...rest }: BtnProps) {
  return (
    <button className={`btn ${variant} ${size} ${className}`} disabled={disabled || busy} {...rest}>
      {busy && <span className="spinner" aria-hidden />}
      {children}
    </button>
  );
}

/** A delete-style button that asks for a second tap instead of a browser dialog. */
export function ConfirmButton({ onConfirm, children, label = "Tap again to confirm", ...rest }: BtnProps & { onConfirm: () => void; label?: string }) {
  const [armed, setArmed] = useState(false);
  return (
    <Button
      variant="quiet"
      size="sm"
      {...rest}
      className={armed ? "danger" : ""}
      onClick={() => (armed ? (setArmed(false), onConfirm()) : setArmed(true))}
      onBlur={() => setArmed(false)}
    >
      {armed ? label : children}
    </Button>
  );
}

export function Field({ label, hint, children, wide }: { label: string; hint?: string; children: ReactNode; wide?: boolean }) {
  return (
    <label className={`field ${wide ? "wide" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export const Input = (p: InputHTMLAttributes<HTMLInputElement>) => <input {...p} />;
export const TextArea = (p: TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea rows={3} {...p} />;
export const Select = (p: SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} />;

export function ErrorNote({ error }: { error: string | null | undefined }) {
  if (!error) return null;
  return <p className="error" role="alert">{error}</p>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children && <div className="empty-body">{children}</div>}
    </div>
  );
}

export function Loading({ what = "Loading" }: { what?: string }) {
  return <p className="muted loading">{what}…</p>;
}

export function Pill({ tone = "flat", children }: { tone?: "good" | "warn" | "bad" | "flat" | "accent"; children: ReactNode }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

export function sellThroughPill(st: number | null | undefined) {
  if (st === null || st === undefined) return <Pill>no sales yet</Pill>;
  if (st >= 0.95) return <Pill tone="good">sold out</Pill>;
  if (st >= 0.7) return <Pill tone="good">strong · {Math.round(st * 100)}%</Pill>;
  if (st >= 0.5) return <Pill tone="warn">steady · {Math.round(st * 100)}%</Pill>;
  return <Pill tone="bad">slow · {Math.round(st * 100)}%</Pill>;
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: "good" | "bad" }) {
  return (
    <div className="stat">
      <span className="eyebrow">{label}</span>
      <span className={`stat-value ${tone ?? ""}`}>{value}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

export function Swatches({ colours }: { colours: Colour[] }) {
  return (
    <div className="swatches">
      {colours.map((c) => (
        <span className="swatch" key={c.name + c.hex}>
          <i style={{ background: /^#[0-9a-f]{6}$/i.test(c.hex) ? c.hex : "transparent" }} />
          {c.name}
        </span>
      ))}
    </div>
  );
}

export function SearchTerms({ terms }: { terms: string[] }) {
  return (
    <ul className="search-terms">
      {terms.map((t) => (
        <li key={t}>
          <span>{t}</span>
          <span className="links">
            {searchLinks(t).map((l) => (
              <a key={l.label} href={l.href} target="_blank" rel="noopener noreferrer">{l.label}</a>
            ))}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function PageHead({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="page-head">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>{title}</h1>
      {children && <div className="page-head-body">{children}</div>}
    </header>
  );
}
