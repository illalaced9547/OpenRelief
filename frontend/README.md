# OpenRelief frontend

React/Vite frontend for the OpenRelief food-security research model. Production: https://openrelief.vercel.app.

## Run locally

Use Node.js 22. From the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite. `npm run build` creates `dist/`.

## What is connected

`src/data/live-predictions.json` contains 14 saved checkpoint outputs, one held-out district example per country. `src/data/modelData.js` is the shared boundary for map coverage, phase colors, country search, details, methodology examples and Global insights.

The UI displays predicted IPC phase 1–5, generated rationale, cutoff, target month and sample provenance. It does not estimate missing values. Countries without model results are uncolored and display “No model data.” Phase numbers are severity classes, not probabilities. All current outputs are historical; country shading identifies a sample's country and is not a nationwide forecast.

The current model supports a three-month horizon from six months of inputs. Synthetic prices, confidence percentages, 30/180-day scenarios and demo chat responses are removed from the application. A calibrated confidence score and observation-level price charts require additional backend outputs.

## Chat and live inference

Copy `.env.example` to an ignored `.env.local` and set `VITE_INFERENCE_URL` to the running HTTPS model server, without credentials. Restart Vite after changing it.

Chat calls Nebius `GET /predict?iso3=XXX` when configured to refresh the selected historical sample. The typed question is matched locally to the returned phase, rationale and provenance; the answer is generated from the trained model’s output, without a second LLM or API key. The saved output is used if the endpoint fails. With no saved output, chat reports that no model data is available. The prediction endpoint accepts a country code rather than a question.

`src/open_relief/serve.py` at the repository root requires CUDA and the checkpoint/dataset on the GPU host. It runs separately from the frontend.

## Annotation Atlas and supporting pages

The Atlas is a contained page with a fixed example selector and one vertical content scroll area. It renders two teacher-annotation examples from map-covered countries (DR Congo and Burkina Faso). The checked-in `src/data/annotationExamples.json` is extracted from `docs/examples/annotation-atlas/examples.json`, preserving original annotation text and provenance. These are training examples whose teacher saw the future label, not the map's held-out predictions. Their charts are bundled local assets.

Global insights summarizes the same saved predictions as the map, not world population risk. Methodology shows the implemented source groups and real saved output examples. Roadmap distinguishes connected functionality from proposed work; planned features are not represented as available data.

## Vercel deployment

Root Directory: `frontend`; install: `npm ci`; build: `npm run build`; output: `dist`. Configure `VITE_INFERENCE_URL` for the intended deployment environment and redeploy. Vite embeds this public URL at build time. Never place credentials in `VITE_*` variables.

The static website, saved model outputs and locally formatted answers run on Vercel. Fresh inference depends on the external CUDA service remaining available. Training is not part of the website build. GitHub pushes trigger deployment only when the Vercel project is connected to the repository.

## Team handoff

- `src/main.jsx`: navigation and interactive map, including bounded vertical and wrapping horizontal movement.
- `src/components/CountryDetails.jsx`: model-only overview, explanation and provenance panels.
- `src/components/ModelPages.jsx`: Global insights and Roadmap.
- `src/components/AnnotationAtlas.jsx`: structured training-example viewer.
- `src/lib/liveModel.js`: snapshot lookup and live inference client.

No Python installation or model weights are needed to run the frontend. `.env*`, `.vercel/`, `node_modules/` and `dist/` are excluded from Git. The frontend is independent of the research pipeline.
