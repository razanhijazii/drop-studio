import { useEffect, useState, type FormEvent } from "react";
import { api, type SaleIn } from "../lib/api";
import { useAction, useResource } from "../lib/hooks";
import { money, toNum, today } from "../lib/format";
import { CHANNELS, SIZES, type Channel, type Size } from "../lib/types";
import { Button, ConfirmButton, Empty, ErrorNote, Field, Input, Loading, PageHead, Select } from "../components/ui";

interface Line { qty: string; size: Size | ""; price: string }

export function Sales() {
  const drops = useResource(() => api.drops());
  const [dropId, setDropId] = useState<number | null>(null);
  const drop = useResource(() => (dropId ? api.drop(dropId) : Promise.resolve(null)), [dropId]);
  const sales = useResource(() => api.sales(), []);
  const [lines, setLines] = useState<Record<number, Line>>({});
  const [date, setDate] = useState(today());
  const [channel, setChannel] = useState<Channel>("store");
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (dropId || !drops.data?.length) return;
    const pick = drops.data.find((d) => d.status === "launched") ?? drops.data.find((d) => d.status === "production") ?? drops.data[0];
    setDropId(pick.id);
  }, [drops.data, dropId]);

  const pieces = drop.data?.looks.flatMap((l) => l.pieces.map((p) => ({ ...p, look: l.position }))) ?? [];
  const line = (id: number): Line => lines[id] ?? { qty: "", size: "", price: "" };
  const setLine = (id: number, patch: Partial<Line>) => setLines({ ...lines, [id]: { ...line(id), ...patch } });

  const record = useAction(async (e: FormEvent) => {
    e.preventDefault();
    const items: SaleIn[] = pieces
      .map((p) => ({ p, l: line(p.id) }))
      .filter(({ l }) => (toNum(l.qty) ?? 0) > 0)
      .map(({ p, l }) => ({
        piece_id: p.id, quantity: Math.round(toNum(l.qty)!), size: l.size || null,
        unit_price: toNum(l.price), sold_on: date, channel,
      }));
    if (!items.length) throw new Error("Enter a quantity for at least one piece.");
    const out = await api.recordSales(items);
    const units = out.reduce((s, x) => s + x.quantity, 0);
    setSaved(`Logged ${units} unit${units === 1 ? "" : "s"} · ${money(out.reduce((s, x) => s + x.quantity * x.unit_price, 0))}`);
    setLines({});
    await sales.reload();
  });

  return (
    <>
      <PageHead eyebrow="Sales" title="Log what sold">
        Enter a day's sales in one go. Price defaults to the list price; type a different one for a discount or a special.
      </PageHead>
      {!drops.data ? <Loading /> : drops.data.length === 0 ? (
        <Empty title="No drops yet">Create a drop with its pieces and prices, then log sales here.<a href="#drops/new">New drop</a></Empty>
      ) : (
        <form className="panel" onSubmit={record.run}>
          <div className="row">
            <Field label="Drop">
              <Select id="sale-drop" value={dropId ?? ""} onChange={(e) => { setDropId(Number(e.target.value)); setLines({}); }}>
                {drops.data.map((d) => <option key={d.id} value={d.id}>{d.name} · {d.status}</option>)}
              </Select>
            </Field>
            <Field label="Date"><Input id="sale-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} max={today()} /></Field>
            <Field label="Where">
              <Select id="sale-channel" value={channel} onChange={(e) => setChannel(e.target.value as Channel)}>
                {CHANNELS.map((c) => <option key={c}>{c}</option>)}
              </Select>
            </Field>
          </div>
          {drop.loading && !drop.data ? <Loading /> : pieces.length === 0 ? (
            <p className="muted">This drop has no pieces yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Look</th><th>Piece</th><th className="num">List price</th><th className="num">Qty</th><th>Size</th><th className="num">Sold at</th></tr></thead>
                <tbody>
                  {pieces.map((p) => (
                    <tr key={p.id}>
                      <td className="mono">{p.look}</td>
                      <td>{p.name || `${p.color} ${p.category}`}</td>
                      <td className="num">{p.price !== null ? money(p.price) : <span className="small" style={{ color: "var(--warn)" }}>no price</span>}</td>
                      <td className="num"><input id={`q-${p.id}`} aria-label="Quantity" type="number" min={0} step={1} inputMode="numeric"
                        value={line(p.id).qty} onChange={(e) => setLine(p.id, { qty: e.target.value })} /></td>
                      <td><select id={`s-${p.id}`} aria-label="Size" value={line(p.id).size} style={{ width: 84 }}
                        onChange={(e) => setLine(p.id, { size: e.target.value as Size | "" })}>
                        <option value="">–</option>{SIZES.map((s) => <option key={s}>{s}</option>)}
                      </select></td>
                      <td className="num"><input id={`p-${p.id}`} aria-label="Sold at price" type="number" min={0} step="0.01" inputMode="decimal"
                        placeholder={p.price?.toString() ?? ""} value={line(p.id).price} onChange={(e) => setLine(p.id, { price: e.target.value })} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="small muted">Selling the same piece in several sizes? Log each size as its own entry so the stock plan learns your size split.</p>
          <div className="row center">
            <Button busy={record.busy} type="submit">Log sales</Button>
            {saved && <span className="small" role="status">{saved}</span>}
          </div>
          <ErrorNote error={record.error} />
        </form>
      )}

      <section className="panel">
        <h2>Recent sales</h2>
        {!sales.data ? <Loading /> : sales.data.length === 0 ? <p className="muted">Nothing logged yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Piece</th><th>Drop</th><th className="num">Qty</th><th>Size</th><th>Where</th><th className="num">Total</th><th></th></tr></thead>
              <tbody>
                {sales.data.map((s) => (
                  <tr key={s.id}>
                    <td className="mono small">{s.sold_on}</td>
                    <td>{s.piece_name}</td>
                    <td className="small muted">{s.drop_name}</td>
                    <td className="num">{s.quantity}</td>
                    <td>{s.size ?? "–"}</td>
                    <td className="small">{s.channel}</td>
                    <td className="num">{money(s.quantity * s.unit_price, { cents: true })}</td>
                    <td><ConfirmButton onConfirm={async () => { await api.deleteSale(s.id); sales.reload(); }}>Undo</ConfirmButton></td>
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
