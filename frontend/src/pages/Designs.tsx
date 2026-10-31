import { useEffect, useRef, useState, type DragEvent } from "react";
import { api, imageUrl } from "../lib/api";
import { useAction, useResource } from "../lib/hooks";
import type { Design } from "../lib/types";
import { Button, ConfirmButton, Empty, ErrorNote, Field, Input, Loading, PageHead, Select, TextArea } from "../components/ui";

const MAX_MB = 5;

export function Designs({ aiEnabled }: { aiEnabled: boolean }) {
  const designs = useResource(() => api.designs());
  const drops = useResource(() => api.drops());
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const [f, setF] = useState({ title: "", note: "", drop_id: "" });
  const [shown, setShown] = useState<Design | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const pick = (fl: File | undefined | null) => {
    if (!fl) return;
    if (fl.size > MAX_MB * 1024 * 1024) { review.setError(`That image is over ${MAX_MB} MB. Export a smaller version.`); return; }
    setFile(fl);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(fl));
  };

  const review = useAction(async () => {
    if (!file) return;
    const form = new FormData();
    form.append("image", file);
    form.append("title", f.title || "Untitled design");
    form.append("note", f.note);
    if (f.drop_id) form.append("drop_id", f.drop_id);
    const d = await api.reviewDesign(form);
    setShown(d);
    await designs.reload();
  });

  return (
    <>
      <PageHead eyebrow="Design review" title="Show me a design">
        Upload a sketch, flat or photo. You'll get scores, what's working, what to change, and brand rules you can save to your DNA.
      </PageHead>
      <section className="panel">
        <div
          className={`dropzone ${over ? "over" : ""}`}
          role="button" tabIndex={0}
          onClick={() => input.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
          onDragOver={(e: DragEvent) => { e.preventDefault(); setOver(true); }}
          onDragLeave={() => setOver(false)}
          onDrop={(e: DragEvent) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]); }}
        >
          {preview ? <img src={preview} alt="Your design" /> : null}
          <span className="muted">{preview ? "Tap to change" : "Tap or drop a PNG, JPEG or WebP (up to 5 MB)"}</span>
          <input ref={input} id="design-file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden
            onChange={(e) => pick(e.target.files?.[0])} />
        </div>
        <div className="row">
          <Field label="Name"><Input id="d-title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="e.g. Look 2 hoodie, cocoa" /></Field>
          <Field label="For drop">
            <Select id="d-drop" value={f.drop_id} onChange={(e) => setF({ ...f, drop_id: e.target.value })}>
              <option value="">Not tied to a drop</option>
              {drops.data?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </Select>
          </Field>
        </div>
        <Field label="What you're going for" wide>
          <TextArea id="d-note" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} placeholder="fabric, fit, the detail you care about" />
        </Field>
        <div><Button busy={review.busy} disabled={!file || !aiEnabled} onClick={() => review.run()}>
          {review.busy ? "Looking closely… up to a minute" : "Get feedback"}
        </Button></div>
        {!aiEnabled && <p className="notice warn">AI is off. Add ANTHROPIC_API_KEY to the backend to review designs.</p>}
        <ErrorNote error={review.error} />
      </section>

      {shown && <Feedback design={shown} />}

      <section className="panel">
        <h2>Past reviews</h2>
        {!designs.data ? <Loading /> : designs.data.length === 0 ? (
          <Empty title="Nothing reviewed yet">Your reviewed designs collect here, and every new review reads the last few as brand memory.</Empty>
        ) : (
          <div className="gallery">
            {designs.data.map((d) => (
              <button key={d.id} onClick={() => { setShown(d); window.scrollTo({ top: 0, behavior: "smooth" }); }} aria-label={`Open review of ${d.title}`}>
                <Thumb path={d.image_url} alt={d.title} />
                <span className="small"><strong>{d.title}</strong></span>
                <span className="small muted">{d.feedback.summary}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function Thumb({ path, alt }: { path: string; alt: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let url: string | null = null;
    imageUrl(path).then((u) => { url = u; setSrc(u); }).catch(() => setFailed(true));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [path]);
  if (failed) return <div className="thumb" aria-label="Image unavailable" />;
  return src ? <img className="thumb" src={src} alt={alt} /> : <div className="thumb" />;
}

function Feedback({ design }: { design: Design }) {
  const fb = design.feedback;
  const [picked, setPicked] = useState<boolean[]>(fb.dna_takeaways.map(() => true));
  const [saved, setSaved] = useState(false);
  const save = useAction(async () => {
    const items = fb.dna_takeaways.filter((_, i) => picked[i]).map((text) => ({ text, source: `review: ${design.title}` }));
    if (items.length) await api.addDna(items);
    setSaved(true);
  });
  const labels: [keyof typeof fb.scores, string][] = [["brand_fit", "Brand fit"], ["trend", "On trend"], ["effortless", "Effortless"], ["wearability", "Wearable"]];

  return (
    <section className="panel">
      <span className="eyebrow">{design.title}</span>
      <h2>{fb.summary}</h2>
      <div className="scores">
        {labels.map(([k, l]) => <div key={k}><span className="eyebrow">{l}</span><b>{fb.scores[k]}<span className="muted small">/10</span></b></div>)}
      </div>
      <div className="grid">
        <div className="stack"><h3>Working</h3><ul style={{ margin: 0, paddingLeft: 18 }}>{fb.works.map((x) => <li key={x}>{x}</li>)}</ul></div>
        <div className="stack"><h3>Change</h3><ul style={{ margin: 0, paddingLeft: 18 }}>{fb.change.map((x) => <li key={x}>{x}</li>)}</ul></div>
      </div>
      <div className="card flat">
        <h3>Add to brand DNA?</h3>
        <p className="small muted">Keep the ones that are true to you. Every future drop and review will follow them.</p>
        {fb.dna_takeaways.map((t, i) => (
          <label className="check" key={t}>
            <input type="checkbox" id={`tk-${design.id}-${i}`} checked={picked[i]} onChange={(e) => setPicked(picked.map((p, j) => (j === i ? e.target.checked : p)))} />
            <span>{t}</span>
          </label>
        ))}
        <div className="row center">
          <Button size="sm" busy={save.busy} disabled={saved} onClick={() => save.run()}>{saved ? "Saved to DNA" : "Save to DNA"}</Button>
          <ConfirmButton onConfirm={async () => { await api.deleteDesign(design.id); window.location.reload(); }}>Delete review</ConfirmButton>
        </div>
        <ErrorNote error={save.error} />
      </div>
    </section>
  );
}
