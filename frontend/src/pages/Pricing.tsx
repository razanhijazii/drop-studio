import { useEffect, useState, type FormEvent } from "react";
import { api } from "../lib/api";
import { useAction, useResource } from "../lib/hooks";
import { money, pct, toNum } from "../lib/format";
import { CATEGORIES, type Category, type PriceSuggestion } from "../lib/types";
import { Button, ConfirmButton, ErrorNote, Field, Input, Loading, PageHead, Select } from "../components/ui";

export function Pricing() {
  const comps = useResource(() => api.competitors());
  const drops = useResource(() => api.drops());
  const [calc, setCalc] = useState({ cost: "", category: "hoodie" as Category, current: "" });
  const [result, setResult] = useState<PriceSuggestion | null>(null);
  const [c, setC] = useState({ brand: "", category: "hoodie" as Category, price: "", note: "" });
  const [dropId, setDropId] = useState<number | null>(null);
  const dropPricing = useResource(() => (dropId ? api.dropPricing(dropId) : Promise.resolve([])), [dropId]);

  useEffect(() => {
    if (!dropId && drops.data?.length) setDropId((drops.data.find((d) => d.status === "draft") ?? drops.data[0]).id);
  }, [drops.data, dropId]);

  const run = useAction(async (e?: FormEvent) => {
    e?.preventDefault();
    const cost = toNum(calc.cost);
    if (!cost) throw new Error("Enter what one piece costs you to make.");
    setResult(await api.suggestPrice(cost, calc.category, toNum(calc.current)));
  });
  const addComp = useAction(async (e: FormEvent) => {
    e.preventDefault();
    const price = toNum(c.price);
    if (!c.brand.trim() || !price) throw new Error("Add the brand and its price.");
    await api.addCompetitor({ ...c, price });
    setC({ ...c, brand: "", price: "", note: "" });
    await comps.reload();
    if (result) await run.run();
  });

  return (
    <>
      <PageHead eyebrow="Pricing" title="What should it sell for?">
        Suggestions start from your cost and margin targets, check against brands you benchmark, and adjust for how fast this category sold before.
      </PageHead>

      <div className="grid">
        <form className="panel" onSubmit={run.run}>
          <h2>Price a piece</h2>
          <div className="row">
            <Field label="Cost to make one" hint="fabric, making, trims, labels, shipping to you">
              <Input id="pc-cost" type="number" min={0} step="0.01" inputMode="decimal" value={calc.cost} onChange={(e) => setCalc({ ...calc, cost: e.target.value })} />
            </Field>
            <Field label="Type">
              <Select id="pc-cat" value={calc.category} onChange={(e) => setCalc({ ...calc, category: e.target.value as Category })}>
                {CATEGORIES.map((x) => <option key={x}>{x}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Price you had in mind (optional)">
            <Input id="pc-current" type="number" min={0} step="0.01" value={calc.current} onChange={(e) => setCalc({ ...calc, current: e.target.value })} />
          </Field>
          <div><Button busy={run.busy} type="submit">Suggest a price</Button></div>
          <ErrorNote error={run.error} />
        </form>

        <section className="panel">
          {result ? <Suggestion r={result} /> : (
            <div className="stack">
              <h2>How it works</h2>
              <p className="muted small">Floor: the lowest price that keeps your minimum margin. Target: the price at your target margin.
                Market: the median of competitor prices you've logged, times your market position. Demand: sold-out categories can carry more;
                slow ones get a smaller run, not a discount. Margins and position are set on the Brand page.</p>
            </div>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>Prices for a drop</h2>
        {!drops.data ? <Loading /> : drops.data.length === 0 ? <p className="muted">No drops yet.</p> : (
          <>
            <Field label="Drop">
              <Select id="pd-drop" value={dropId ?? ""} onChange={(e) => setDropId(Number(e.target.value))}>
                {drops.data.map((d) => <option key={d.id} value={d.id}>{d.name} · {d.status}</option>)}
              </Select>
            </Field>
            {!dropPricing.data ? <Loading /> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Look</th><th>Piece</th><th className="num">Cost</th><th className="num">Your price</th><th className="num">Suggested</th><th className="num">Margin</th><th>Note</th><th></th></tr></thead>
                  <tbody>
                    {dropPricing.data.map((p) => (
                      <tr key={p.piece_id}>
                        <td className="mono">{p.look}</td>
                        <td>{p.name}</td>
                        <td className="num">{money(p.unit_cost, { cents: true })}</td>
                        <td className="num">{money(p.price)}</td>
                        <td className="num"><strong>{p.suggestion ? money(p.suggestion.recommended) : "–"}</strong></td>
                        <td className="num">{p.suggestion ? pct(p.suggestion.margin_at_recommended) : "–"}</td>
                        <td className="small muted">{p.suggestion ? (p.suggestion.warnings[0] ?? "") : "Add a unit cost on the drop page"}</td>
                        <td>{p.suggestion && p.suggestion.recommended !== p.price && (
                          <Button size="sm" variant="ghost" onClick={async () => { await api.updatePiece(p.piece_id, { price: p.suggestion!.recommended }); dropPricing.reload(); }}>Use</Button>
                        )}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <section className="panel">
        <h2>Brands you benchmark</h2>
        <p className="muted small">Log real list prices from brands your customer also buys. Three or more per type gives a steady market read. Check prices are current.</p>
        <form className="row" onSubmit={addComp.run}>
          <Field label="Brand"><Input id="cp-brand" value={c.brand} onChange={(e) => setC({ ...c, brand: e.target.value })} placeholder="e.g. Essentials" /></Field>
          <Field label="Type">
            <Select id="cp-cat" value={c.category} onChange={(e) => setC({ ...c, category: e.target.value as Category })}>
              {CATEGORIES.map((x) => <option key={x}>{x}</option>)}
            </Select>
          </Field>
          <Field label="Price"><Input id="cp-price" type="number" min={0} step="0.01" value={c.price} onChange={(e) => setC({ ...c, price: e.target.value })} /></Field>
          <Field label="Note"><Input id="cp-note" value={c.note} onChange={(e) => setC({ ...c, note: e.target.value })} placeholder="where you saw it" /></Field>
          <Button variant="ghost" busy={addComp.busy} type="submit">Add</Button>
        </form>
        <ErrorNote error={addComp.error} />
        {comps.data && comps.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Type</th><th>Brand</th><th className="num">Price</th><th>Note</th><th></th></tr></thead>
              <tbody>
                {comps.data.map((x) => (
                  <tr key={x.id}>
                    <td>{x.category}</td><td>{x.brand}</td><td className="num">{money(x.price)}</td><td className="small muted">{x.note}</td>
                    <td><ConfirmButton onConfirm={async () => { await api.deleteCompetitor(x.id); comps.reload(); }}>Remove</ConfirmButton></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function Suggestion({ r }: { r: PriceSuggestion }) {
  const points = [r.floor, r.cost_target, r.recommended, r.market_low, r.market_high].filter((x): x is number => x !== null);
  const lo = Math.min(...points) * 0.85, hi = Math.max(...points) * 1.1;
  const at = (v: number) => `${((v - lo) / (hi - lo)) * 100}%`;
  return (
    <div className="stack">
      <span className="eyebrow">Suggested price</span>
      <div className="row center" style={{ gap: 16 }}>
        <span className="price-big">{money(r.recommended)}</span>
        <span className="small">{pct(r.margin_at_recommended)} margin · {r.markup}× cost</span>
      </div>
      <div className="range" aria-hidden>
        <div className="track" />
        {r.market_low !== null && r.market_high !== null && (
          <div className="band" style={{ left: at(r.market_low), width: `calc(${at(r.market_high)} - ${at(r.market_low)})` }} />
        )}
        <div className="mark" style={{ left: at(r.floor) }}><span>floor {money(r.floor)}</span></div>
        <div className="mark rec" style={{ left: at(r.recommended) }} />
      </div>
      <ul className="small" style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
        {r.reasons.map((x) => <li key={x}>{x}</li>)}
      </ul>
      {r.warnings.map((w) => <p className="notice warn small" key={w}>{w}</p>)}
      {r.current_margin !== null && <p className="small muted">Your price would give a {pct(r.current_margin)} margin.</p>}
    </div>
  );
}
