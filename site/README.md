# BoothMate site + Beat Breakdown

The public BoothMate website, hosted on Netlify.

- `design/Main.dc.html`: the landing page, same file as the Claude Design canvas. `node scripts/build-site.mjs design/Main.dc.html` turns it into `public/index.html` (rendered by `public/dc-lite.js` + morphdom).
- `public/breakdown.html`: the Beat Breakdown results page.
- `netlify/functions/`: `checkout` (YouTube link -> Stripe Checkout, $22.99), `breakdown` (status / start), `run-breakdown-background` (Gemini analysis, up to 15 min).

## Netlify environment variables (set them in Netlify, never in code)
| Name | What |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `STRIPE_SECRET_KEY` | Stripe restricted key (Checkout Sessions: write) |
| `GEMINI_MODEL` | optional, default `gemini-4-hydrogen` |
| `BEAT_BREAKDOWN_PRICE_ID` | optional Stripe Price id; otherwise $22.99 is charged inline |

Tests: `npm install && npm test` (backend), `node tests/browser/render.mjs` and `node tests/browser/results.mjs` (pages, need `jsdom`).
