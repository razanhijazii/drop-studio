# Drop Studio

A design and business system for a premium basics brand that releases **four looks every two months**
(hoodies, t-shirts, sweatshirts, sweatpants).

| Area | What it does |
|---|---|
| **Trends** | Log trend signals (polls, sell-outs, reports). Claude ranks 3–5 directions for your launch month, with fit score, colours, search terms for Pinterest/TikTok, and the try-hard version to avoid. |
| **Drops** | Generate four complete looks from a trend: fabric and GSM specs, one signature detail per look, store mood (lighting, scent, sound, display, a ritual). Edit everything. |
| **Design review** | Upload a sketch, flat or photo and get scores, what works, what to change, and brand rules you can save to your DNA. |
| **Brand DNA** | Profile and rules that every AI feature reads, so recommendations learn your taste. |
| **Sales** | Log a day's sales in one go, per piece, with size, channel and actual price. |
| **Money** | Revenue, gross profit, profit after other costs, cash back vs everything spent, stock left at cost, revenue by month and channel, break-even units. |
| **Pricing** | Price suggestions from cost and margin targets, the brands you benchmark, and past sell-through. |
| **Stock plan** | Units per piece and size for the next drop, learned from what sold, plus the cash needed up front. |

## How the numbers work

The calculations are plain, tested Python in `backend/app/services/`:

- **`finance.py`**: *Profit on sales* = revenue − cost of the units sold − other costs.
  *Cash back* = revenue − everything spent on production − other costs. Unsold stock is cash on a shelf, so it's shown separately at cost.
- **`pricing.py`**: floor = cost ÷ (1 − minimum margin); target = cost ÷ (1 − target margin). If you've logged competitor prices,
  the price follows their median × your market position, capped at their upper quartile. Sold-out categories get +4–8%;
  slow ones get −5% and a warning to make fewer rather than discount. Rounded to clean prices (5s under 100, 10s above), never below the floor.
- **`planner.py`**: first drop = a baseline per piece (default 30). After that, demand per piece by type, newest drop weighted 60/30/10.
  Sold-out pieces are scaled up 1.4× (demand you couldn't serve), plus a 10% buffer, rounded to 5, minimum 10. Sizes blend your real
  size sales with a standard curve, trusting your data more as it grows. Your manufacturer's minimum order is flagged.

All margins, market position, first-drop size and minimum order are editable on the Brand page.

## Project layout

```
backend/            FastAPI + SQLAlchemy + Alembic
  app/main.py       app, auth, routes
  app/models.py     database tables
  app/services/     finance, pricing, planner (pure functions), ai (Claude), context (brand memory)
  app/routers/      HTTP endpoints
  alembic/          database migrations
  tests/            45 tests: calculations, every API flow, the Claude client with mocked HTTP
frontend/           React + TypeScript, bundled with esbuild
  src/pages/        one file per page
  src/lib/api.ts    typed API client
render.yaml         one-click deploy of both services on Render
```

## Run it locally

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.seed            # add --demo for a sample launched drop with sales
export ANTHROPIC_API_KEY=sk-ant-...   # optional; AI features are off without it
uvicorn app.main:app --reload  # http://localhost:8000/docs

# frontend (new terminal)
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Locally there's no password unless you set `APP_PASSWORD`.

Tests: `cd backend && pytest` · Types: `cd frontend && npm run typecheck`

## Deploy (Render + Neon)

1. **Database.** Create a free Postgres at [neon.tech](https://neon.tech) and copy its connection string.
   Render's free Postgres is deleted after 30 days, so it isn't used here.
2. **Render.** New > Blueprint > choose this repo. Fill in:
   - `DATABASE_URL`: the Neon string
   - `APP_PASSWORD`: what you'll sign in with
   - `ANTHROPIC_API_KEY`: from [console.anthropic.com](https://console.anthropic.com)
   - `FRONTEND_ORIGIN`: the web service URL, e.g. `https://drop-studio-web.onrender.com`
   - `API_URL` (on drop-studio-web): the API URL, e.g. `https://drop-studio-api.onrender.com`
3. On its first start the API loads the starter brand concepts and trend signals by itself (only into an empty database).

The free API service sleeps after 15 minutes idle; the first request after that takes about a minute while it wakes up.

## Changing the database

Edit `app/models.py`, then:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Render runs `alembic upgrade head` on every deploy, so your data is migrated, not wiped.

## Notes

- The AI can't browse the web. It reasons from your trend signals, brand DNA, past drops and reviews. Keep feeding it signals.
- Design images are stored in the database (5 MB limit each), so they survive redeploys.
- AI calls use the `ANTHROPIC_MODEL` setting (default `claude-sonnet-5-5`) and are billed to your Anthropic account per use.
