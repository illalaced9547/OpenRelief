# OpenRelief frontend

Local React frontend for exploring illustrative food insecurity forecasts.

## Run locally

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Run `npm run build` to produce a production build.

The interface opens on a dark landing page with the React Bits True Focus title and a Get started button. The full-page neutral gray map dashboard uses translucent country overlays, a map-scoped React Bits Target Cursor, hover probabilities, country search, risk filters, three forecast horizons, and floating country details. Country selection preserves the current map position and zoom. Use the wheel or buttons to zoom up to 10×, drag to pan, and reset to return to the world view. A non-passive wheel listener prevents browser zoom gestures over the map from scaling the page. Navigation includes Global insights, methodology, and a proposed Roadmap. The landing call to action uses React Bits Glass Surface. The brand returns to the landing page.

All probabilities and signal values are synthetic. The horizon control applies a fixed demo adjustment. Gray countries have no demo data. These categories are UI conventions, not IPC classifications.

## Model integration

The `forecasts` object in `src/main.jsx` is the placeholder boundary for countries the
checkpoint hasn't evaluated. Country keys are zero-padded ISO 3166-1 numeric codes matching
the world map; the 14 countries the fine-tuned checkpoint was evaluated on also carry an
`iso3` field.

**The map and chat show real model output for those 14 countries — from a static snapshot,
not a live call.** `frontend/src/data/live-predictions.json` is a batch-generated file (one
real forward pass per country through `src/open_relief/serve.py`'s checkpoint), read
synchronously by `frontend/src/lib/liveModel.js`. The map's risk number for those countries
is a direct linear mapping of the real predicted IPC phase (1 Minimal - 5 Famine -> 0-100),
not a calibrated probability; the price/confidence cards are replaced with the real
cutoff/rationale/recommended actions. Every other country keeps the original synthetic
fixtures. Everything is labeled MODEL FORECAST vs DEMO throughout — no network call happens
at runtime, so nothing depends on the Nebius endpoint staying up.

To refresh the snapshot (intended cadence: daily/weekly against a live cutoff, not
per-request): `python scripts/generate_live_predictions.py <endpoint-url>` from the repo
root, then rebuild the frontend. The endpoint itself never needs to run continuously.

No OpenAI key is needed for this frontend. Future credentials belong on the backend, never in browser code. `.env` files are ignored by Git.

Map geometry: Natural Earth via `world-atlas`. Title: React Bits True Focus installed using the shadcn registry. The production frontend is deployed at https://openrelief.vercel.app.

## Explanations, confidence and chat

Country details have Outlook, Explanation and Sources views. The price observation has a separate 30-day comparison period from the forecast horizon. Risk and confidence are distinct; confidence is a synthetic uncalibrated score, not validated forecast accuracy. Scenarios are fictional and do not assert that the events described actually occurred.

The Global insights preview uses the same explanation fixtures and is designed for a future model-generated feed with provenance. Suggested backend fields include: country code, forecast horizon, event definition, risk probability, confidence score and calibration definition, price series/unit/currency, hypothesis, alternatives, explanation method, source records/URLs/observation dates, model version and generation timestamp. None of the source categories are mandatory fixed drivers.

The Ask OpenRelief chat icon smoothly swaps the country intelligence panel for a conversation in the same footprint. Closing chat restores the previous country detail view; the draft and conversation persist while navigating dashboard views. Hidden panels are inert and excluded from accessibility navigation, and reduced-motion preferences disable transitions. Ask OpenRelief is an interactive frontend demo, not a connected LLM. Questions and sample responses stay in local React state and are not sent externally. Supported demo prompts cover price, reasons, confidence and sources; other prompts explain the limitation. Each message retains the country and horizon at send time. To enable live questions, the colleague's backend should accept the question, country, forecast horizon and conversation, then return a grounded answer with source references. No API contract or credentials are currently configured.

## Vercel deployment

This directory is a standalone Vite app. For a Git-connected Vercel project, set Root Directory to `frontend`; install with `npm ci`, build with `npm run build`, and use output directory `dist`. No environment variables are required — the real model output is a static file committed to the repo (see Model integration above). The Python model pipeline is not deployed with this frontend at all.

The overview map wraps horizontally using repeated world copies, with bounded vertical movement and a small overscroll allowance. Horizontal trackpad gestures pan; vertical wheel gestures zoom. Landing, Global insights, Roadmap and the Methodology page use a decorative blurred flat world map with colored country regions and no percentage markers. The interactive risk overview remains a flat map.

Methodology is a full navigation page using the shared flat map background. Five example input categories connect visually to a model card and three fictional country outputs. Country output buttons open their 90-day demo outlook; input cards are static, with equally styled connections and no selection highlights or popups. The diagram describes the intended system, not a completed model integration.

Methodology connector dots run in a synchronized four-second loop: all five inputs travel to the model over the first two seconds, followed by all three output dots over the next two. Reduced-motion preferences hide these animations.

The methodology diagram uses a fixed-height compact layout with its explanatory paragraphs removed. Search and forecast controls share the map header row. Decorative and interactive maps use shared viewport-relative dimensions so the default view matches the landing background; panning and zoom still work from that baseline.

## Team handoff

This folder is independent of the Python pipeline in `../src/open_relief/`. Frontend work does not require installing Python, downloading model weights, or running training. Use Node.js 22 and the committed npm lockfile; run `npm ci` and `npm run build` inside this folder to validate changes.

- `src/main.jsx`: application navigation, interactive map and demo country forecasts.
- `src/components/`: shared UI, methodology diagram, country search and chat.
- `src/data/explanations.js`: demo explanations, source placeholders and local chat responses.
- `vercel.json`: Vite build configuration for this folder.

The current research pipeline predicts district-level IPC phase three months ahead. The UI's country risk percentages and 30/90/180-day choices are illustrative, not a direct representation of those outputs. Before connecting the model, agree on geographic aggregation, supported horizons, probability calibration and provenance. Unsupported countries should remain unavailable rather than receive synthetic live values.

Vercel has been deployed through the CLI. A GitHub push does not imply automatic deployment unless the Vercel project is connected to this repository. When connecting it, use `frontend` as Root Directory. Local `.vercel/` account/project metadata, environment files, dependencies and build output are excluded from Git. Never put secrets in `VITE_*` variables, which are exposed to the browser.
