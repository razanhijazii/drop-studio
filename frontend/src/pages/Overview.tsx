import { api } from "../lib/api";
import { useResource } from "../lib/hooks";
import { money, monthLabel, pct } from "../lib/format";
import { Empty, ErrorNote, Loading, PageHead, Pill, Stat, sellThroughPill } from "../components/ui";
import { MonthChart } from "../components/MonthChart";

export function Overview() {
  const summary = useResource(() => api.summary());
  const drops = useResource(() => api.drops());
  const signals = useResource(() => api.signals());
  const dna = useResource(() => api.dna());

  if (summary.error) return <ErrorNote error={summary.error} />;
  if (!summary.data || !drops.data) return <Loading />;

  const s = summary.data;
  const current = drops.data.find((d) => d.status === "launched") ?? drops.data.find((d) => d.status === "production");
  const draft = drops.data.find((d) => d.status === "draft");

  const steps: { done: boolean; text: string; href: string }[] = [
    { done: (dna.data?.length ?? 0) > 0, text: "Write your brand DNA and profile", href: "#brand" },
    { done: (signals.data?.length ?? 0) >= 3, text: "Log at least 3 trend signals", href: "#trends" },
    { done: drops.data.length > 0, text: "Build your first drop of 4 looks", href: "#drops/new" },
    { done: s.totals.production_spend > 0, text: "Add unit costs, prices and quantities", href: draft ? `#drops/${draft.id}` : "#drops" },
    { done: s.totals.units_sold > 0, text: "Log your first sales", href: "#sales" },
  ];
  const open = steps.filter((x) => !x.done);

  return (
    <>
      <PageHead eyebrow="Overview" title="Where the brand stands">
        Money across every drop, what's live now, and what to do next.
      </PageHead>

      <div className="stats">
        <Stat label="Revenue" value={money(s.totals.revenue)} sub={`${s.totals.units_sold} units sold`} />
        <Stat label="Profit on sales" value={money(s.totals.net_profit)} tone={s.totals.net_profit < 0 ? "bad" : undefined}
          sub={`gross margin ${pct(s.totals.gross_margin)}`} />
        <Stat label="Cash back" value={money(s.totals.cash_back)} tone={s.totals.cash_back < 0 ? "bad" : "good"}
          sub="revenue minus everything spent" />
        <Stat label="Stock on the shelf" value={money(s.totals.stock_value_at_cost)} sub="unsold units, at cost" />
      </div>

      {open.length > 0 && (
        <section className="panel">
          <h2>Next steps</h2>
          <div className="list">
            {steps.map((x) => (
              <a key={x.text} href={x.href} className="list-item" style={{ color: "inherit", textDecoration: "none" }}>
                <Pill tone={x.done ? "good" : "flat"}>{x.done ? "done" : "to do"}</Pill>
                <span className="grow">{x.text}</span>
              </a>
            ))}
          </div>
        </section>
      )}

      <div className="grid">
        <section className="panel">
          <div className="panel-head">
            <div><span className="eyebrow">Live drop</span><h2>{current ? current.name : "Nothing live yet"}</h2></div>
            {current && sellThroughPill(current.sell_through)}
          </div>
          {current ? (
            <>
              <p className="muted">{current.trend} · {monthLabel(current.launch_month)}</p>
              <div className="row">
                <Stat label="Revenue" value={money(current.revenue)} />
                <Stat label="Profit" value={money(current.net_profit)} />
              </div>
              <a href={`#drops/${current.id}`}>Open drop</a>
            </>
          ) : (
            <p className="muted">When a drop goes on sale, mark it launched and its numbers show here.</p>
          )}
        </section>
        <section className="panel">
          <div className="panel-head">
            <div><span className="eyebrow">Up next</span><h2>{draft ? draft.name : "No draft drop"}</h2></div>
          </div>
          {draft ? (
            <>
              <p className="muted">{draft.trend || "No trend set"} · {monthLabel(draft.launch_month)}</p>
              <div className="row">
                <a href={`#drops/${draft.id}`}>Edit looks</a>
                <a href="#stock">Plan stock</a>
                <a href="#pricing">Set prices</a>
              </div>
            </>
          ) : (
            <p className="muted">Scout a trend and build the next four looks. <a href="#trends">Start with trends</a>.</p>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>Revenue by month</h2>
        {s.by_month.length ? <MonthChart data={s.by_month} /> : (
          <Empty title="No sales yet">Log sales on the Sales page and they'll chart here by month.</Empty>
        )}
      </section>
    </>
  );
}
