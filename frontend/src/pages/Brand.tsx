import { useEffect, useState, type FormEvent } from "react";
import { api } from "../lib/api";
import { useAction, useResource } from "../lib/hooks";
import type { Profile } from "../lib/types";
import { Button, ConfirmButton, ErrorNote, Field, Input, Loading, PageHead, TextArea } from "../components/ui";

export function Brand({ onSaved }: { onSaved: () => void }) {
  const profile = useResource(() => api.profile());
  const dna = useResource(() => api.dna());
  const [p, setP] = useState<Profile | null>(null);
  const [rule, setRule] = useState("");
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => { if (profile.data) setP(profile.data); }, [profile.data]);

  const save = useAction(async (e: FormEvent) => {
    e.preventDefault();
    if (!p) return;
    await api.saveProfile(p);
    setSavedAt(new Date().toLocaleTimeString());
    onSaved();
  });
  const addRule = useAction(async (e: FormEvent) => {
    e.preventDefault();
    if (rule.trim().length < 2) return;
    await api.addDna([{ text: rule.trim() }]);
    setRule("");
    await dna.reload();
  });

  if (!p) return <Loading />;
  const text = (k: keyof Profile) => (e: { target: { value: string } }) => setP({ ...p, [k]: e.target.value });
  const ratio = (k: "target_margin" | "min_margin" | "market_position") => (e: { target: { value: string } }) =>
    setP({ ...p, [k]: Number(e.target.value) / 100 });

  return (
    <>
      <PageHead eyebrow="Brand DNA" title="Who the brand is">
        Everything here is read by every recommendation: trend ranking, drop design, design reviews and pricing.
      </PageHead>

      <form className="panel" onSubmit={save.run}>
        <h2>Profile</h2>
        <div className="row">
          <Field label="Brand name"><Input id="b-name" value={p.name} onChange={text("name")} /></Field>
          <Field label="Who wears it"><Input id="b-customer" value={p.customer} onChange={text("customer")} /></Field>
        </div>
        <Field label="The brand in one line" wide><TextArea id="b-line" value={p.one_liner} onChange={text("one_liner")} /></Field>
        <Field label="Concepts and themes" wide><TextArea id="b-concepts" value={p.concepts} onChange={text("concepts")} /></Field>
        <div className="row">
          <Field label="Price feel"><Input id="b-price" value={p.price_position} onChange={text("price_position")} /></Field>
          <Field label="Never do"><Input id="b-never" value={p.never_do} onChange={text("never_do")} /></Field>
        </div>

        <hr className="divider" />
        <h2>Business settings</h2>
        <div className="row">
          <Field label="Currency" hint="3-letter code, e.g. USD"><Input id="b-cur" maxLength={3} value={p.currency} onChange={(e) => setP({ ...p, currency: e.target.value.toUpperCase() })} /></Field>
          <Field label="Target margin %" hint="premium basics usually 65–80%"><Input id="b-tm" type="number" min={1} max={99} value={Math.round(p.target_margin * 100)} onChange={ratio("target_margin")} /></Field>
          <Field label="Minimum margin %" hint="never price below this"><Input id="b-mm" type="number" min={1} max={99} value={Math.round(p.min_margin * 100)} onChange={ratio("min_margin")} /></Field>
        </div>
        <div className="row">
          <Field label="Market position %" hint="100 = same as brands you benchmark, 90 = a bit under"><Input id="b-mp" type="number" min={30} max={150} value={Math.round(p.market_position * 100)} onChange={ratio("market_position")} /></Field>
          <Field label="First-drop units per piece"><Input id="b-fd" type="number" min={1} value={p.first_drop_units} onChange={(e) => setP({ ...p, first_drop_units: Number(e.target.value) })} /></Field>
          <Field label="Manufacturer minimum per style" hint="0 if none"><Input id="b-moq" type="number" min={0} value={p.min_order_qty} onChange={(e) => setP({ ...p, min_order_qty: Number(e.target.value) })} /></Field>
        </div>
        <div className="row center">
          <Button busy={save.busy} type="submit">Save profile</Button>
          {savedAt && <span className="small muted" role="status">Saved at {savedAt}</span>}
        </div>
        <ErrorNote error={save.error} />
      </form>

      <section className="panel">
        <h2>DNA rules</h2>
        <p className="muted small">Rules learned from your feedback and decisions. Turn one off to stop the AI using it without deleting it.</p>
        <form className="row" onSubmit={addRule.run}>
          <Field label="Add a rule"><Input id="dna-new" value={rule} onChange={(e) => setRule(e.target.value)} placeholder="e.g. Logos stay tonal, never contrast" /></Field>
          <Button variant="ghost" busy={addRule.busy} type="submit">Add</Button>
        </form>
        <ErrorNote error={addRule.error} />
        {!dna.data ? <Loading /> : (
          <div className="list">
            {dna.data.map((r) => (
              <div className="list-item" key={r.id} style={{ opacity: r.active ? 1 : 0.55 }}>
                <input type="checkbox" id={`dna-${r.id}`} aria-label="Active" checked={r.active}
                  onChange={async (e) => { await api.updateDna(r.id, { text: r.text, source: r.source, active: e.target.checked }); dna.reload(); }} />
                <div className="grow"><span>{r.text}</span><span className="small muted">{r.source}</span></div>
                <ConfirmButton onConfirm={async () => { await api.deleteDna(r.id); dna.reload(); }}>Remove</ConfirmButton>
              </div>
            ))}
            {dna.data.length === 0 && <p className="muted">No rules yet.</p>}
          </div>
        )}
      </section>
    </>
  );
}
