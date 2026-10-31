import { useEffect, useState, type FormEvent } from "react";
import { api, getToken, handleUnauthorized, setToken } from "./lib/api";
import { useResource, useRoute } from "./lib/hooks";
import { setCurrency } from "./lib/format";
import type { AppConfig } from "./lib/types";
import { Button, ErrorNote, Field, Input, Loading } from "./components/ui";
import { Overview } from "./pages/Overview";
import { Trends } from "./pages/Trends";
import { Drops } from "./pages/Drops";
import { DropDetail } from "./pages/DropDetail";
import { NewDrop } from "./pages/NewDrop";
import { Sales } from "./pages/Sales";
import { Money } from "./pages/Money";
import { Pricing } from "./pages/Pricing";
import { Stock } from "./pages/Stock";
import { Designs } from "./pages/Designs";
import { Brand } from "./pages/Brand";

const NAV: { group: string; items: [string, string][] }[] = [
  { group: "Create", items: [["overview", "Overview"], ["trends", "Trends"], ["drops", "Drops"], ["designs", "Design review"]] },
  { group: "Run", items: [["sales", "Sales"], ["money", "Money"], ["pricing", "Pricing"], ["stock", "Stock plan"]] },
  { group: "Brand", items: [["brand", "Brand DNA"]] },
];

export function App() {
  const config = useResource<AppConfig>(() => api.config());
  const [authed, setAuthed] = useState(!!getToken());

  useEffect(() => handleUnauthorized(() => setAuthed(false)), []);

  if (config.error) {
    return (
      <div className="login">
        <div className="stack" style={{ maxWidth: 420 }}>
          <h1>Drop Studio</h1>
          <ErrorNote error={config.error} />
          <Button variant="ghost" onClick={() => config.reload()}>Try again</Button>
        </div>
      </div>
    );
  }
  if (!config.data) return <div className="login"><Loading what="Waking up the studio" /></div>;
  if (config.data.auth_required && !authed) return <Login onDone={() => setAuthed(true)} />;
  return <Shell config={config.data} onSignOut={() => { setToken(null); setAuthed(false); }} />;
}

function Login({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.login(password);
      setToken(token);
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="login">
      <form onSubmit={submit}>
        <span className="eyebrow">Four looks, every two months</span>
        <h1>Drop Studio</h1>
        <Field label="Password">
          <Input id="password" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} autoFocus />
        </Field>
        <ErrorNote error={error} />
        <Button busy={busy} type="submit">Sign in</Button>
      </form>
    </div>
  );
}

function Shell({ config, onSignOut }: { config: AppConfig; onSignOut: () => void }) {
  const route = useRoute();
  const [menu, setMenu] = useState(false);
  const profile = useResource(() => api.profile());
  const [, force] = useState(0);

  useEffect(() => {
    if (profile.data) { setCurrency(profile.data.currency); force((n) => n + 1); }
  }, [profile.data]);
  useEffect(() => setMenu(false), [route.join("/")]);

  const [page, id, sub] = route;
  const brand = profile.data?.name || "Your brand";
  let view;
  switch (page) {
    case "overview": view = <Overview />; break;
    case "trends": view = <Trends aiEnabled={config.ai_enabled} />; break;
    case "drops":
      view = id === "new" ? <NewDrop aiEnabled={config.ai_enabled} trend={sub ? decodeURIComponent(sub) : ""} />
        : id ? <DropDetail id={Number(id)} /> : <Drops />;
      break;
    case "sales": view = <Sales />; break;
    case "money": view = <Money />; break;
    case "pricing": view = <Pricing />; break;
    case "stock": view = <Stock />; break;
    case "designs": view = <Designs aiEnabled={config.ai_enabled} />; break;
    case "brand": view = <Brand onSaved={() => profile.reload()} />; break;
    default: view = <Overview />;
  }

  return (
    <div className="shell">
      <div className="topbar">
        <strong>{brand}</strong>
        <Button variant="ghost" size="sm" onClick={() => setMenu((m) => !m)} aria-expanded={menu}>
          {menu ? "Close" : "Menu"}
        </Button>
      </div>
      <nav className={`nav ${menu ? "open" : ""}`} aria-label="Main">
        <div className="brandmark">
          <span className="eyebrow">Drop Studio</span>
          <strong>{brand}</strong>
        </div>
        {NAV.map((g) => (
          <div className="nav-group" key={g.group}>
            <span className="eyebrow">{g.group}</span>
            {g.items.map(([href, label]) => (
              <a key={href} href={`#${href}`} aria-current={page === href ? "page" : undefined}>{label}</a>
            ))}
          </div>
        ))}
        <div className="nav-foot">
          {!config.ai_enabled && <span className="small muted">AI is off: add ANTHROPIC_API_KEY on the server.</span>}
          {config.auth_required && <Button variant="quiet" size="sm" onClick={onSignOut}>Sign out</Button>}
        </div>
      </nav>
      <main className="main">
        <div className="page" key={route.join("/")}>{view}</div>
      </main>
    </div>
  );
}
