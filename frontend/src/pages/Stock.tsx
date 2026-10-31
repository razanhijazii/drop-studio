import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useResource } from "../lib/hooks";
import { money, pct } from "../lib/format";
import { SIZES } from "../lib/types";
import { Button, ErrorNote, Field, Loading, PageHead, Pill, Select, Stat, sellThroughPill } from "../components/ui";

export function Stock() {
  const drops = useResource(() => api.drops());
  const [dropId, setDropId] = useState<number | null>(null);
  const plan = useResource(() => api.stockPlan(dropId ?? undefined), [dropId]);
  const [applied, setApplied] = useState(false);

  useEffect(() => {
    const target = drops.data?.find((d) => d.status === "draft" || d.status === "production");
    if (target && dropId === null) setDropId(target.id);
  }, [drops.data, dropId]);

  if (plan.error) return <ErrorNote error={plan.error} />;
  if (!plan.data) return <Loading />;
  const p = plan.data;

  const apply = async () => {
    if (!p.drop) return;
    await Promise.all(p.drop.pieces.map((x) => api.updatePiece(x.piece_id, { units_made: x.units, made_by_size: x.by_size })));
    setApplied(true);
    plan.reload();
  };

  return (
    <>
      <PageHead eyebrow="Stock plan" title="How much to make">
        {p.first_drop
          ? "First drop: start small so you learn what sells without tying up cash. The plan updates itself once a drop is launched and its sales are logged."
          : `Based on ${p.based_on.join(", ")}, newest weighted most. Sold-out pieces get more, slow ones less, and sizes follow what people bought.`}
      </PageHead>

      <section className="panel">
        <h2>Per piece, by type</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Type</th><th className="num">Make per piece</th><th>Last time</th><th>Why</th></tr></thead>
            <tbody>
              {p.categories.map((c) => (
                <tr key={c.category}>
                  <td>{c.category}</td>
                  <td className="num"><strong>{c.units_per_piece}</strong>{c.below_moq && <> <Pill tone="warn">under MOQ</Pill></>}</td>
                  <td>{c.sell_through === null ? <span className="small muted">no history</span> : sellThroughPill(c.sell_through)}</td>
                  <td className="small">{c.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <span className="eyebrow">Size split {p.size_data_weight ? `(${pct(p.size_data_weight)} from your sales)` : "(standard curve until you log sizes)"}</span>
        <div className="table-wrap">
          <table>
            <thead><tr>{SIZES.map((s) => <th className="num" key={s}>{s}</th>)}</tr></thead>
            <tbody><tr>{SIZES.map((s) => <td className="num" key={s}>{pct(p.size_curve[s])}</td>)}</tr></tbody>
          </table>
        </div>
        {p.min_order_qty > 0 && p.categories.some((c) => c.below_moq) && (
          <p className="notice warn">Your manufacturer's minimum is {p.min_order_qty} per style. Rather than overbuying, consider fewer styles: make one hero piece for a look instead of two.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <div><h2>Production order for a drop</h2><p className="small muted">Units per piece, split by size, and the cash you need up front.</p></div>
          {drops.data && drops.data.length > 0 && (
            <Field label="Drop">
              <Select id="stock-drop" value={dropId ?? ""} onChange={(e) => { setDropId(Number(e.target.value)); setApplied(false); }}>
                {drops.data.map((d) => <option key={d.id} value={d.id}>{d.name} · {d.status}</option>)}
              </Select>
            </Field>
          )}
        </div>
        {!p.drop ? <p className="muted">Create a draft drop to get its production order.</p> : (
          <>
            <div className="stats">
              <Stat label="Total units" value={p.drop.total_units} />
              <Stat label="Cash needed" value={money(p.drop.cash_needed)} sub={p.drop.missing_costs.length ? `missing cost for ${p.drop.missing_costs.length} piece(s)` : "at your unit costs"} />
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Look</th><th>Piece</th><th className="num">Make</th>{SIZES.map((s) => <th className="num" key={s}>{s}</th>)}<th className="num">Cost</th><th className="num">Now set</th></tr></thead>
                <tbody>
                  {p.drop.pieces.map((x) => (
                    <tr key={x.piece_id}>
                      <td className="mono">{x.look}</td>
                      <td>{x.name}</td>
                      <td className="num"><strong>{x.units}</strong></td>
                      {SIZES.map((s) => <td className="num" key={s}>{x.by_size[s] ?? "–"}</td>)}
                      <td className="num">{money(x.cash_needed)}</td>
                      <td className="num muted">{x.current_units ?? "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="row center">
              <Button variant="ghost" onClick={apply} disabled={applied}>{applied ? "Applied to the drop" : "Use these quantities"}</Button>
              <span className="small muted">Sets units made and the size breakdown on every piece. You can still edit them.</span>
            </div>
          </>
        )}
      </section>
    </>
  );
}
