import { Fragment } from "react";
import type { Colour, LookIn, StoreMood } from "../lib/types";
import { SearchTerms, Swatches } from "./ui";

/** Read-only view of a drop's creative direction: palette, looks, store mood, moodboard. */
export function ConceptView({ story, palette, looks, store, moodboard, avoid }: {
  story: string; palette: Colour[]; looks?: LookIn[]; store: StoreMood; moodboard: string[]; avoid: string[];
}) {
  return (
    <div className="stack" style={{ gap: 16 }}>
      {story && <p style={{ maxWidth: "68ch" }}>{story}</p>}
      {palette.length > 0 && <Swatches colours={palette} />}
      {looks && looks.length > 0 && (
        <div className="grid">
          {looks.map((l) => (
            <article className="card" key={l.position}>
              <span className="look-n">LOOK {l.position}</span>
              <h3>{l.name}</h3>
              {l.pieces.map((p, i) => (
                <dl className="spec" key={i}>
                  <dt>{p.category}</dt><dd>{p.name || p.color}{p.fit ? ` · ${p.fit}` : ""}</dd>
                  <dt>Colour</dt><dd>{p.color}</dd>
                  <dt>Fabric</dt><dd>{p.fabric}{p.gsm ? <span className="mono"> · {p.gsm} gsm</span> : null}</dd>
                </dl>
              ))}
              {l.signature_detail && <p className="small"><strong>Signature:</strong> {l.signature_detail}</p>}
            </article>
          ))}
        </div>
      )}
      <div className="grid">
        <StoreCard store={store} />
        {(moodboard.length > 0 || avoid.length > 0) && (
          <div className="card flat">
            <h3>Moodboard searches</h3>
            <SearchTerms terms={moodboard} />
            {avoid.length > 0 && <p className="small muted"><strong>Stay away from:</strong> {avoid.join("; ")}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

export function StoreCard({ store }: { store: StoreMood }) {
  const rows = (["lighting", "scent", "sound", "display", "ritual"] as const).filter((k) => store[k]);
  if (!rows.length) return null;
  return (
    <div className="card flat">
      <h3>How the store feels</h3>
      <dl className="spec">
        {rows.map((k) => <Fragment key={k}><dt>{k}</dt><dd>{store[k]}</dd></Fragment>)}
      </dl>
    </div>
  );
}
