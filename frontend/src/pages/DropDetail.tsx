import { useState, type FormEvent } from "react";
import { api } from "../lib/api";
import { go, useAction, useResource } from "../lib/hooks";
import { money, monthLabel, pct, toNum, today } from "../lib/format";
import { CATEGORIES, STATUSES, type Category, type Drop, type Piece, type PriceSuggestion, type Status } from "../lib/types";
import {
  Button, ConfirmButton, Empty, ErrorNote, Field, Input, Loading, PageHead, Pill, Select, Stat, TextArea, sellThroughPill,
} from "../components/ui";
import { ConceptView } from "../components/DropConcept";
import { MonthChart } from "../components/MonthChart";
import { statusTone } from "./Drops";

type Tab = "looks" | "concept" | "money";

export function DropDetail({ id }: { id: number }) {
  const drop = useResource(() => api.drop(id), [id]);
  const [tab, setTab] = useState<Tab>("looks");

  if (drop.error) return <ErrorNote error={drop.error} />;
  if (!drop.data) return <Loading />;
  const d = drop.data;

  return (
    <>
      <PageHead eyebrow={`${d.trend || "No trend"} · ${monthLabel(d.launch_month)}`} title={d.name}>
        <StatusBar drop={d} onChange={drop.setData} />
      </PageHead>
      <div className="tabs" role="tablist">
        {([["looks", "Looks & costs"], ["concept", "Concept & store"], ["money", "Money"]] as [Tab, string][]).map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {tab === "looks" && <LooksEditor drop={d} reload={drop.reload} />}
      {tab === "concept" && <ConceptEditor drop={d} onSaved={drop.setData} />}
      {tab === "money" && <DropMoneyView drop={d} reload={drop.reload} />}
      <div className="row">
        <ConfirmButton label="Tap again: deletes the drop and its sales" onConfirm={async () => { await api.deleteDrop(d.id); go("drops"); }}>
          Delete drop
        </ConfirmButton>
      </div>
    </>
  );
}

function StatusBar({ drop, onChange }: { drop: Drop; onChange: (d: Drop) => void }) {
  const set = useAction(async (status: Status) => onChange(await api.updateDrop(drop.id, { status })));
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="row center">
        <Pill tone={statusTone[drop.status]}>{drop.status}</Pill>
        {drop.launched_on && <span className="small">launched {new Date(drop.launched_on).toLocaleDateString()}</span>}
        <Select id="drop-status" aria-label="Status" value={drop.status} style={{ width: "auto" }}
          onChange={(e) => set.run(e.target.value as Status)} disabled={set.busy}>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
      </div>
      {drop.status === "draft" && <span className="small">Set costs, prices and quantities, then move it to production.</span>}
      {drop.status === "production" && <span className="small">When it goes on sale, mark it launched. Sales will start counting toward the stock plan.</span>}
      <ErrorNote error={set.error} />
    </div>
  );
}

// ------------------------------------------------------------------ looks

function LooksEditor({ drop, reload }: { drop: Drop; reload: () => Promise<void> }) {
  const addLook = useAction(async () => {
    const used = new Set(drop.looks.map((l) => l.position));
    const position = [1, 2, 3, 4].find((p) => !used.has(p)) ?? 4;
    await api.addLook(drop.id, { position, name: `Look ${position}`, signature_detail: "", pieces: [] });
    await reload();
  });
  return (
    <div className="stack" style={{ gap: 16 }}>
      {drop.looks.length === 0 && <Empty title="No looks yet">Add up to four looks, each with 2–3 pieces.</Empty>}
      {drop.looks.map((look) => (
        <section className="panel" key={look.id}>
          <LookHeader look={look} reload={reload} />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Piece</th><th>Colour · fabric</th><th className="num">Cost</th><th className="num">Price</th>
                  <th className="num">Margin</th><th className="num">Made</th><th></th>
                </tr>
              </thead>
              <tbody>
                {look.pieces.map((p) => <PieceRow key={p.id} piece={p} reload={reload} />)}
              </tbody>
            </table>
          </div>
          <AddPiece lookId={look.id} reload={reload} />
        </section>
      ))}
      {drop.looks.length < 4 && (
        <div><Button variant="ghost" busy={addLook.busy} onClick={() => addLook.run()}>Add look {drop.looks.length + 1}</Button></div>
      )}
      <ErrorNote error={addLook.error} />
    </div>
  );
}

function LookHeader({ look, reload }: { look: Drop["looks"][number]; reload: () => Promise<void> }) {
  const [name, setName] = useState(look.name);
  const [sig, setSig] = useState(look.signature_detail);
  const save = useAction(async () => {
    if (name !== look.name || sig !== look.signature_detail) await api.updateLook(look.id, { name, signature_detail: sig });
  });
  const totalPrice = look.pieces.reduce((s, p) => s + (p.price ?? 0), 0);
  return (
    <div className="stack">
      <div className="row between">
        <span className="look-n">LOOK {look.position}{totalPrice ? ` · full outfit ${money(totalPrice)}` : ""}</span>
        <ConfirmButton onConfirm={async () => { await api.deleteLook(look.id); reload(); }}>Remove look</ConfirmButton>
      </div>
      <div className="row">
        <Field label="Name"><Input id={`look-name-${look.id}`} value={name} onChange={(e) => setName(e.target.value)} onBlur={() => save.run()} /></Field>
        <Field label="Signature detail"><Input id={`look-sig-${look.id}`} value={sig} onChange={(e) => setSig(e.target.value)} onBlur={() => save.run()} placeholder="the one quiet detail" /></Field>
      </div>
      <ErrorNote error={save.error} />
    </div>
  );
}

function PieceRow({ piece, reload }: { piece: Piece; reload: () => Promise<void> }) {
  const [v, setV] = useState({
    unit_cost: piece.unit_cost?.toString() ?? "",
    price: piece.price?.toString() ?? "",
    units_made: piece.units_made?.toString() ?? "",
  });
  const [suggestion, setSuggestion] = useState<PriceSuggestion | null>(null);
  const save = useAction(async (field: keyof typeof v) => {
    const val = toNum(v[field]);
    if (val === piece[field]) return;
    await api.updatePiece(piece.id, { [field]: field === "units_made" && val !== null ? Math.round(val) : val });
    await reload();
  });
  const suggest = useAction(async () => {
    const cost = toNum(v.unit_cost);
    if (!cost) throw new Error("Enter the unit cost first.");
    setSuggestion(await api.suggestPrice(cost, piece.category, toNum(v.price)));
  });

  const cost = toNum(v.unit_cost), price = toNum(v.price);
  const margin = cost !== null && price ? 1 - cost / price : null;

  return (
    <>
      <tr>
        <td><strong>{piece.name || piece.category}</strong><br /><span className="small muted">{piece.category}{piece.fit ? ` · ${piece.fit}` : ""}</span></td>
        <td className="small">{piece.color}{piece.fabric ? ` · ${piece.fabric}` : ""}{piece.gsm ? ` · ${piece.gsm} gsm` : ""}</td>
        {(["unit_cost", "price", "units_made"] as const).slice(0, 2).map((f) => (
          <td className="num" key={f}>
            <input id={`${f}-${piece.id}`} aria-label={f === "unit_cost" ? "Unit cost" : "Price"} type="number" min={0} step="0.01" inputMode="decimal"
              value={v[f]} onChange={(e) => setV({ ...v, [f]: e.target.value })} onBlur={() => save.run(f)} />
          </td>
        ))}
        <td className="num">{margin === null ? "–" : <span style={{ color: margin < 0.55 ? "var(--bad)" : undefined }}>{pct(margin)}</span>}</td>
        <td className="num">
          <input id={`units-${piece.id}`} aria-label="Units made" type="number" min={0} step={1} inputMode="numeric"
            value={v.units_made} onChange={(e) => setV({ ...v, units_made: e.target.value })} onBlur={() => save.run("units_made")} />
        </td>
        <td>
          <div className="row" style={{ flexWrap: "nowrap", gap: 2 }}>
            <Button variant="quiet" size="sm" busy={suggest.busy} onClick={() => suggest.run()}>Suggest price</Button>
            <ConfirmButton onConfirm={async () => { await api.deletePiece(piece.id); reload(); }}>Remove</ConfirmButton>
          </div>
        </td>
      </tr>
      {(suggestion || suggest.error || save.error) && (
        <tr>
          <td colSpan={7}>
            <ErrorNote error={suggest.error || save.error} />
            {suggestion && (
              <div className="row center" style={{ gap: 14 }}>
                <span>Suggested <strong className="mono">{money(suggestion.recommended)}</strong> ({pct(suggestion.margin_at_recommended)} margin)</span>
                <span className="small muted">{suggestion.reasons[suggestion.reasons.length - 1]}</span>
                {suggestion.warnings[0] && <span className="small" style={{ color: "var(--warn)" }}>{suggestion.warnings[0]}</span>}
                <Button size="sm" variant="ghost" onClick={async () => {
                  setV({ ...v, price: String(suggestion.recommended) });
                  await api.updatePiece(piece.id, { price: suggestion.recommended });
                  setSuggestion(null);
                  reload();
                }}>Use this price</Button>
                <Button size="sm" variant="quiet" onClick={() => setSuggestion(null)}>Dismiss</Button>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function AddPiece({ lookId, reload }: { lookId: number; reload: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ category: "t-shirt" as Category, name: "", color: "", fabric: "", gsm: "" });
  const add = useAction(async (e: FormEvent) => {
    e.preventDefault();
    await api.addPiece(lookId, {
      category: f.category, name: f.name, color: f.color, fit: "", fabric: f.fabric, gsm: toNum(f.gsm),
      unit_cost: null, price: null, units_made: null, made_by_size: {},
    });
    setF({ category: "t-shirt", name: "", color: "", fabric: "", gsm: "" });
    setOpen(false);
    await reload();
  });
  if (!open) return <div><Button variant="quiet" size="sm" onClick={() => setOpen(true)}>Add piece</Button></div>;
  return (
    <form className="row" onSubmit={add.run}>
      <Field label="Type">
        <Select id={`np-cat-${lookId}`} value={f.category} onChange={(e) => setF({ ...f, category: e.target.value as Category })}>
          {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
        </Select>
      </Field>
      <Field label="Name"><Input id={`np-name-${lookId}`} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      <Field label="Colour"><Input id={`np-color-${lookId}`} value={f.color} onChange={(e) => setF({ ...f, color: e.target.value })} /></Field>
      <Field label="Fabric"><Input id={`np-fabric-${lookId}`} value={f.fabric} onChange={(e) => setF({ ...f, fabric: e.target.value })} /></Field>
      <Field label="GSM"><Input id={`np-gsm-${lookId}`} type="number" value={f.gsm} onChange={(e) => setF({ ...f, gsm: e.target.value })} /></Field>
      <Button busy={add.busy} type="submit">Add</Button>
      <Button variant="quiet" type="button" onClick={() => setOpen(false)}>Cancel</Button>
      <ErrorNote error={add.error} />
    </form>
  );
}

// ------------------------------------------------------------------ concept

function ConceptEditor({ drop, onSaved }: { drop: Drop; onSaved: (d: Drop) => void }) {
  const [editing, setEditing] = useState(false);
  const [f, setF] = useState({
    name: drop.name, trend: drop.trend, launch_month: drop.launch_month, story: drop.story, store: drop.store,
    moodboard: drop.moodboard.join("\n"), avoid: drop.avoid.join("\n"),
  });
  const save = useAction(async () => {
    const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
    onSaved(await api.updateDrop(drop.id, { ...f, moodboard: lines(f.moodboard), avoid: lines(f.avoid) }));
    setEditing(false);
  });
  if (!editing) {
    return (
      <section className="panel">
        <div className="row between"><h2>Concept</h2><Button variant="ghost" size="sm" onClick={() => setEditing(true)}>Edit</Button></div>
        <ConceptView story={drop.story} palette={drop.palette} store={drop.store} moodboard={drop.moodboard} avoid={drop.avoid}
          looks={drop.looks.map((l) => ({ ...l, pieces: l.pieces }))} />
      </section>
    );
  }
  return (
    <section className="panel">
      <div className="row">
        <Field label="Drop name"><Input id="c-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Trend"><Input id="c-trend" value={f.trend} onChange={(e) => setF({ ...f, trend: e.target.value })} /></Field>
        <Field label="Launch month"><Input id="c-month" type="month" value={f.launch_month} onChange={(e) => setF({ ...f, launch_month: e.target.value })} /></Field>
      </div>
      <Field label="Story" wide><TextArea id="c-story" value={f.story} onChange={(e) => setF({ ...f, story: e.target.value })} /></Field>
      <div className="grid">
        {(["lighting", "scent", "sound", "display", "ritual"] as const).map((k) => (
          <Field key={k} label={k}><Input id={`c-${k}`} value={f.store[k]} onChange={(e) => setF({ ...f, store: { ...f.store, [k]: e.target.value } })} /></Field>
        ))}
      </div>
      <div className="row">
        <Field label="Moodboard searches" hint="one per line"><TextArea id="c-mood" value={f.moodboard} onChange={(e) => setF({ ...f, moodboard: e.target.value })} /></Field>
        <Field label="Stay away from" hint="one per line"><TextArea id="c-avoid" value={f.avoid} onChange={(e) => setF({ ...f, avoid: e.target.value })} /></Field>
      </div>
      <div className="row">
        <Button busy={save.busy} onClick={() => save.run()}>Save</Button>
        <Button variant="quiet" onClick={() => setEditing(false)}>Cancel</Button>
      </div>
      <ErrorNote error={save.error} />
    </section>
  );
}

// ------------------------------------------------------------------ money

function DropMoneyView({ drop, reload }: { drop: Drop; reload: () => Promise<void> }) {
  const m = useResource(() => api.dropMoney(drop.id), [drop.id, drop.expenses.length]);
  const [e, setE] = useState({ label: "", amount: "", spent_on: today() });
  const addExp = useAction(async (ev: FormEvent) => {
    ev.preventDefault();
    const amount = toNum(e.amount);
    if (!e.label.trim() || amount === null) throw new Error("Give the expense a name and an amount.");
    await api.addExpense(drop.id, { label: e.label, amount, spent_on: e.spent_on || null });
    setE({ label: "", amount: "", spent_on: today() });
    await reload();
  });

  if (m.error) return <ErrorNote error={m.error} />;
  if (!m.data) return <Loading />;
  const x = m.data;
  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="stats">
        <Stat label="Revenue" value={money(x.revenue)} sub={`${x.units_sold} of ${x.units_made} sold`} />
        <Stat label="Profit on sales" value={money(x.net_profit)} tone={x.net_profit < 0 ? "bad" : undefined} sub={`gross margin ${pct(x.gross_margin)}`} />
        <Stat label="Cash back" value={money(x.cash_back)} tone={x.cash_back < 0 ? "bad" : "good"}
          sub={x.break_even_units_left ? `${x.break_even_units_left} more sales to break even` : x.payback !== null ? `${pct(x.payback)} of spend recovered` : undefined} />
        <Stat label="Stock left" value={money(x.stock_value_at_cost)} sub="at cost" />
      </div>
      {x.missing_costs.length > 0 && (
        <p className="notice warn">No unit cost for {x.missing_costs.join(", ")}. Profit is overstated until you add them on the Looks tab.</p>
      )}
      <section className="panel">
        <h2>By piece</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Piece</th><th className="num">Sold</th><th className="num">Left</th><th>Sell-through</th><th className="num">Revenue</th><th className="num">Profit</th><th className="num">Avg price</th></tr></thead>
            <tbody>
              {x.pieces.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}{p.oversold && <> <Pill tone="bad">more sold than made</Pill></>}</td>
                  <td className="num">{p.units_sold}</td>
                  <td className="num">{p.units_left ?? "–"}</td>
                  <td>{sellThroughPill(p.sell_through)}</td>
                  <td className="num">{money(p.revenue)}</td>
                  <td className="num">{money(p.gross_profit)}</td>
                  <td className="num">{money(p.avg_selling_price)}{p.discount_rate ? <span className="muted small"> (−{pct(p.discount_rate)})</span> : null}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {x.by_month.length > 0 && <section className="panel"><h2>Revenue by month</h2><MonthChart data={x.by_month} /></section>}
      <section className="panel">
        <h2>Other costs</h2>
        <p className="muted small">Things that aren't one garment: launch night, packaging, store setup, ads, shoots.</p>
        {drop.expenses.length > 0 && (
          <div className="list">
            {drop.expenses.map((ex) => (
              <div className="list-item" key={ex.id}>
                <span className="grow">{ex.label}<span className="small muted">{ex.spent_on ? new Date(ex.spent_on).toLocaleDateString() : ""}</span></span>
                <span className="mono">{money(ex.amount, { cents: true })}</span>
                <ConfirmButton onConfirm={async () => { await api.deleteExpense(ex.id); reload(); }}>Remove</ConfirmButton>
              </div>
            ))}
          </div>
        )}
        <form className="row" onSubmit={addExp.run}>
          <Field label="What"><Input id="exp-label" value={e.label} onChange={(ev) => setE({ ...e, label: ev.target.value })} placeholder="e.g. Launch night" /></Field>
          <Field label="Amount"><Input id="exp-amount" type="number" min={0} step="0.01" value={e.amount} onChange={(ev) => setE({ ...e, amount: ev.target.value })} /></Field>
          <Field label="Date"><Input id="exp-date" type="date" value={e.spent_on} onChange={(ev) => setE({ ...e, spent_on: ev.target.value })} /></Field>
          <Button variant="ghost" busy={addExp.busy} type="submit">Add cost</Button>
        </form>
        <ErrorNote error={addExp.error} />
      </section>
    </div>
  );
}
