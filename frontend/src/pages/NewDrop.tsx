import { useState } from "react";
import { api } from "../lib/api";
import { go, useAction } from "../lib/hooks";
import { monthsAhead } from "../lib/format";
import type { DropIn } from "../lib/types";
import { Button, ErrorNote, Field, Input, PageHead, TextArea } from "../components/ui";
import { ConceptView } from "../components/DropConcept";

const blank = (trend: string, month: string): DropIn => ({
  name: "", trend, launch_month: month, story: "", palette: [], moodboard: [], avoid: [],
  store: { lighting: "", scent: "", sound: "", display: "", ritual: "" },
  looks: [1, 2, 3, 4].map((position) => ({
    position, name: `Look ${position}`, signature_detail: "",
    pieces: [
      { category: "hoodie", name: "", color: "", fit: "", fabric: "", gsm: null, unit_cost: null, price: null, units_made: null, made_by_size: {} },
      { category: "sweatpants", name: "", color: "", fit: "", fabric: "", gsm: null, unit_cost: null, price: null, units_made: null, made_by_size: {} },
    ],
  })),
});

export function NewDrop({ aiEnabled, trend: initialTrend }: { aiEnabled: boolean; trend: string }) {
  const [trend, setTrend] = useState(initialTrend);
  const [month, setMonth] = useState(monthsAhead(2));
  const [direction, setDirection] = useState("");
  const [draft, setDraft] = useState<DropIn | null>(null);

  const generate = useAction(async () => setDraft(await api.generateDrop(trend, month, direction)));
  const save = useAction(async (d: DropIn) => {
    const saved = await api.createDrop(d);
    go(`drops/${saved.id}`);
  });

  return (
    <>
      <PageHead eyebrow="New drop" title="Four looks, one story">
        Generate a direction from a trend, then edit everything after saving. Or start blank and design it yourself.
      </PageHead>

      <section className="panel">
        <div className="row">
          <Field label="Trend"><Input id="nd-trend" value={trend} onChange={(e) => setTrend(e.target.value)} placeholder="e.g. Cocoa calm" /></Field>
          <Field label="Launch month"><Input id="nd-month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} /></Field>
        </div>
        <Field label="Your direction" wide>
          <TextArea id="nd-direction" value={direction} onChange={(e) => setDirection(e.target.value)}
            placeholder="optional: a feeling, a memory, a fabric you want, pieces to include" />
        </Field>
        <div className="row">
          <Button busy={generate.busy} disabled={!aiEnabled || trend.trim().length < 2 || !month} onClick={() => generate.run()}>
            {generate.busy ? "Designing… up to a minute" : draft ? "Generate again" : "Generate four looks"}
          </Button>
          <Button variant="ghost" busy={save.busy} disabled={!month}
            onClick={() => save.run({ ...blank(trend, month), name: trend ? `${trend} drop` : "Untitled drop" })}>
            Start blank
          </Button>
        </div>
        {!aiEnabled && <p className="notice warn">AI is off, so only blank drops are available.</p>}
        <ErrorNote error={generate.error || save.error} />
      </section>

      {draft && (
        <section className="panel">
          <div className="panel-head">
            <div><span className="eyebrow">{draft.trend} · draft</span>
              <Input id="nd-name" aria-label="Drop name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                style={{ fontFamily: "var(--display)", fontStretch: "112%", fontWeight: 700, fontSize: 22 }} />
            </div>
            <Button busy={save.busy} onClick={() => save.run(draft)} disabled={!draft.name.trim()}>Save drop</Button>
          </div>
          <ConceptView {...draft} />
        </section>
      )}
    </>
  );
}
