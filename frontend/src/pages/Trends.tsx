import { useState, type FormEvent } from "react";
import { api } from "../lib/api";
import { useAction, useResource } from "../lib/hooks";
import { monthLabel, monthsAhead } from "../lib/format";
import type { TrendReport } from "../lib/types";
import {
  Button, ConfirmButton, Empty, ErrorNote, Field, Input, Loading, PageHead, Pill, SearchTerms, Swatches, TextArea,
} from "../components/ui";

export function Trends({ aiEnabled }: { aiEnabled: boolean }) {
  const signals = useResource(() => api.signals());
  const reports = useResource(() => api.reports());
  const [form, setForm] = useState({ title: "", source: "", note: "", url: "" });
  const [month, setMonth] = useState(monthsAhead(2));
  const [hint, setHint] = useState("");
  const [shown, setShown] = useState<TrendReport | null>(null);

  const add = useAction(async (e: FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    await api.addSignal(form);
    setForm({ title: "", source: "", note: "", url: "" });
    await signals.reload();
  });
  const scout = useAction(async () => {
    const r = await api.scout(month, hint);
    setShown(r);
    await reports.reload();
  });

  const report = shown ?? reports.data?.[0];

  return (
    <>
      <PageHead eyebrow="Trends" title="What should the next drop be about?">
        Log the evidence you see, then let the scout rank directions for your launch month against your brand DNA and past sales.
      </PageHead>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Scout the next drop</h2>
            <p className="muted small">The scout reasons from your signals and brand memory. It can't browse, so fresh signals keep it current.</p>
          </div>
        </div>
        <div className="row">
          <Field label="Drop launches"><Input id="scout-month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} /></Field>
          <Field label="Anything to lean into"><Input id="scout-hint" value={hint} onChange={(e) => setHint(e.target.value)} placeholder="optional, e.g. more colour this time" /></Field>
          <Button busy={scout.busy} disabled={!aiEnabled || !month} onClick={() => scout.run()}>
            {scout.busy ? "Ranking… about a minute" : "Rank trends"}
          </Button>
        </div>
        {!aiEnabled && <p className="notice warn">AI is off. Add ANTHROPIC_API_KEY to the backend to use the scout.</p>}
        <ErrorNote error={scout.error} />
      </section>

      {report && (
        <section className="stack">
          <div className="row between">
            <div className="stack" style={{ gap: 2 }}>
              <span className="eyebrow">Ranked for {monthLabel(report.launch_month)} · {new Date(report.created_at).toLocaleDateString()}</span>
              <p>{report.result.summary}</p>
            </div>
            {(reports.data?.length ?? 0) > 1 && (
              <select aria-label="Earlier reports" value={report.id} style={{ width: "auto" }}
                onChange={(e) => setShown(reports.data!.find((r) => r.id === Number(e.target.value)) ?? null)}>
                {reports.data!.map((r) => (
                  <option key={r.id} value={r.id}>{monthLabel(r.launch_month)} · {new Date(r.created_at).toLocaleDateString()}</option>
                ))}
              </select>
            )}
          </div>
          <div className="grid">
            {report.result.trends.map((t) => (
              <article className="card" key={t.name}>
                <div className="row between"><h3>{t.name}</h3><Pill tone={t.lifespan === "micro" ? "warn" : "accent"}>{t.lifespan}</Pill></div>
                <div className="fitbar"><span>Fit</span><span className="track"><span style={{ width: `${t.fit}%` }} /></span><span>{t.fit}</span></div>
                <p>{t.why}</p>
                <Swatches colours={t.colours} />
                <p className="small"><strong>Our take:</strong> {t.our_take}</p>
                <p className="small muted"><strong>Avoid:</strong> {t.avoid}</p>
                <span className="eyebrow">Search for inspiration</span>
                <SearchTerms terms={t.search_terms} />
                <a className="btn primary sm" href={`#drops/new/${encodeURIComponent(t.name)}`} style={{ alignSelf: "flex-start", textDecoration: "none" }}>
                  Build a drop from this
                </a>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="panel">
        <h2>Trend signals</h2>
        <form className="stack" onSubmit={add.run}>
          <div className="row">
            <Field label="Signal"><Input id="sig-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Poll: 68% picked brown over grey" /></Field>
            <Field label="Source"><Input id="sig-source" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder="Poll, store, report, TikTok" /></Field>
          </div>
          <Field label="Detail" wide><TextArea id="sig-note" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="Numbers, where you saw it, who's wearing it" /></Field>
          <div className="row">
            <Field label="Link (optional)"><Input id="sig-url" type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /></Field>
            <Button variant="ghost" busy={add.busy} type="submit" disabled={!form.title.trim()}>Add signal</Button>
          </div>
          <ErrorNote error={add.error} />
        </form>
        <hr className="divider" />
        {signals.loading && !signals.data ? <Loading /> : signals.data?.length ? (
          <div className="list">
            {signals.data.map((s) => (
              <div className="list-item" key={s.id}>
                <div className="grow">
                  <strong>{s.title}</strong>
                  {s.note && <span className="muted small">{s.note}</span>}
                  <span className="small muted">
                    {s.source}{s.url && <> · <a href={s.url} target="_blank" rel="noopener noreferrer">source</a></>} · {new Date(s.created_at).toLocaleDateString()}
                  </span>
                </div>
                <ConfirmButton onConfirm={async () => { await api.deleteSignal(s.id); signals.reload(); }}>Remove</ConfirmButton>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="No signals yet">Add what you notice: Instagram poll results, what friends ask for, what sold out somewhere, a report stat.</Empty>
        )}
      </section>
    </>
  );
}
