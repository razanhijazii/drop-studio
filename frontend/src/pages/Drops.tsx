import { api } from "../lib/api";
import { useResource } from "../lib/hooks";
import { money, monthLabel } from "../lib/format";
import { Empty, ErrorNote, Loading, PageHead, Pill, sellThroughPill } from "../components/ui";
import type { Status } from "../lib/types";

export const statusTone: Record<Status, "flat" | "warn" | "good" | "accent"> = {
  draft: "flat", production: "warn", launched: "good", closed: "accent",
};

export function Drops() {
  const drops = useResource(() => api.drops());
  return (
    <>
      <PageHead eyebrow="Drops" title="Every drop, four looks each">
        <div className="row center">
          <span>Draft, produce, launch, close. Each drop keeps its own looks, costs and sales.</span>
          <a className="btn primary sm" href="#drops/new" style={{ textDecoration: "none" }}>New drop</a>
        </div>
      </PageHead>
      <ErrorNote error={drops.error} />
      {!drops.data ? <Loading /> : drops.data.length === 0 ? (
        <Empty title="No drops yet">
          Start from a trend the scout ranked, or build one from scratch.
          <div className="row"><a href="#trends">Scout trends</a><a href="#drops/new">Build from scratch</a></div>
        </Empty>
      ) : (
        <section className="panel" style={{ paddingBlock: 4 }}>
          {drops.data.map((d) => (
            <a className="drop-row" key={d.id} href={`#drops/${d.id}`}>
              <div className="stack" style={{ gap: 4 }}>
                <h3>{d.name}</h3>
                <div className="meta">
                  <span>{d.trend || "no trend"}</span>
                  <span>{monthLabel(d.launch_month)}</span>
                  {d.units_sold > 0 && <span>{d.units_sold} sold · {money(d.revenue)}</span>}
                </div>
              </div>
              <div className="row center" style={{ justifyContent: "flex-end" }}>
                {d.status !== "draft" && sellThroughPill(d.sell_through)}
                <Pill tone={statusTone[d.status]}>{d.status}</Pill>
              </div>
            </a>
          ))}
        </section>
      )}
    </>
  );
}
