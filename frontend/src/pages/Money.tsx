import { api } from "../lib/api";
import { useResource } from "../lib/hooks";
import { money, monthLabel, pct } from "../lib/format";
import { Empty, ErrorNote, Loading, PageHead, Stat, sellThroughPill } from "../components/ui";
import { MonthChart } from "../components/MonthChart";

export function Money() {
  const s = useResource(() => api.summary());
  if (s.error) return <ErrorNote error={s.error} />;
  if (!s.data) return <Loading />;
  const { totals, drops, by_month, by_channel } = s.data;
  const channelTotal = Object.values(by_channel).reduce((a, b) => a + b, 0);

  return (
    <>
      <PageHead eyebrow="Money" title="Revenue, profit and cash">
        Profit on sales asks whether each sale makes money. Cash back asks whether you've recovered everything you spent,
        including stock that hasn't sold yet.
      </PageHead>
      <div className="stats">
        <Stat label="Revenue" value={money(totals.revenue)} sub={`${totals.units_sold} units`} />
        <Stat label="Gross profit" value={money(totals.gross_profit)} sub={`margin ${pct(totals.gross_margin)}`} />
        <Stat label="Other costs" value={money(totals.expenses)} sub="launches, packaging, ads" />
        <Stat label="Profit on sales" value={money(totals.net_profit)} tone={totals.net_profit < 0 ? "bad" : undefined} />
        <Stat label="Spent on production" value={money(totals.production_spend)} />
        <Stat label="Cash back" value={money(totals.cash_back)} tone={totals.cash_back < 0 ? "bad" : "good"} sub={`${money(totals.stock_value_at_cost)} still on the shelf`} />
      </div>

      <section className="panel">
        <h2>Revenue by month</h2>
        {by_month.length ? <MonthChart data={by_month} /> : <Empty title="No sales yet">Log sales and they'll chart here.</Empty>}
      </section>

      <section className="panel">
        <h2>By drop</h2>
        {drops.length === 0 ? <p className="muted">No drops yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Drop</th><th>Sell-through</th><th className="num">Revenue</th><th className="num">Margin</th>
                  <th className="num">Profit</th><th className="num">Cash back</th><th>Best seller</th></tr>
              </thead>
              <tbody>
                {drops.map((d) => (
                  <tr key={d.id}>
                    <td><a href={`#drops/${d.id}`}>{d.name}</a><br /><span className="small muted">{d.status} · {monthLabel(d.launch_month)}</span></td>
                    <td>{d.units_made ? sellThroughPill(d.sell_through) : <span className="small muted">no quantities</span>}</td>
                    <td className="num">{money(d.revenue)}</td>
                    <td className="num">{pct(d.gross_margin)}</td>
                    <td className="num">{money(d.net_profit)}</td>
                    <td className="num" style={{ color: d.cash_back < 0 ? "var(--bad)" : undefined }}>
                      {money(d.cash_back)}
                      {d.break_even_units_left ? <><br /><span className="small muted">{d.break_even_units_left} sales to break even</span></> : null}
                    </td>
                    <td className="small">{d.best_seller ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {drops.some((d) => d.missing_costs.length) && (
          <p className="notice warn">Some pieces have no unit cost, so their profit is overstated. Open the drop and fill them in.</p>
        )}
      </section>

      {channelTotal > 0 && (
        <section className="panel">
          <h2>Where it sells</h2>
          <div className="stack">
            {Object.entries(by_channel).sort((a, b) => b[1] - a[1]).map(([ch, v]) => (
              <div className="fitbar" key={ch}>
                <span style={{ width: 80 }}>{ch}</span>
                <span className="track"><span style={{ width: `${(v / channelTotal) * 100}%` }} /></span>
                <span style={{ width: 90, textAlign: "right" }}>{money(v)}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
