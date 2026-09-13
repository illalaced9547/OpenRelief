# Submission checklist and ownership

The challenge slides require a working demo, code with training configuration, a checkpoint
or adapter, dataset documentation, and a short held-out evaluation against a baseline.
The completed frontend is now in `frontend/`; it still uses synthetic fixtures until model integration.
Training, checkpoint delivery and final evaluation are owned by the training model/workstream.

| Deliverable | Owner / remaining action | Acceptance check |
|---|---|---|
| World-map demo | **Done**: map shows the checkpoint's real batch-generated forecast for the 14 test-set countries (static snapshot, no network call), synthetic fixtures for the rest; chat calls the checkpoint live per question, falling back to the snapshot then to demo answers | Works after a fresh start; map has no network dependency; model vs demo answers are labeled per-message and per-country |
| Annotation demonstration | Documentation workstream: charted training examples and cached generated arguments | [Atlas](examples/annotation-atlas/README.md) and offline HTML load; exact examples and request hashes included |
| Code and configuration | All owners: record submitted commit and checkpoint's actual code version | README command matches the delivered configuration; no conflict markers or credentials |
| Checkpoint / adapter | **Done**: `best_model.pt` retrieved to `artifacts/nebius/all-sources/`, SHA-256 `a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10`; loaded and proven to run via a Nebius AI endpoint | Loads in a fresh process (proven by generating the committed prediction snapshot) and produces valid examples |
| Evaluation | **Done**: pretrained-vs-fine-tuned on the full 2,230-example test set ([FINDING-pretrained-baseline.md](FINDING-pretrained-baseline.md)); ablations on a 256-example cohort ([FINDING-portwatch-signal.md](FINDING-portwatch-signal.md)); fine-tuned full-2,230 reruns were in flight at submission time, folded in only if they landed | Identical sample IDs for compared models, explicit split/class support and no unsupported causal claims |
| Dataset documentation | Documentation/data owners: dataset card, provenance, coverage; resolve HFID upstream terms | [Dataset card](DATASET_CARD.md) matches manifests; source access and reuse claims are accurate |
| Presentation / fallback | Team: rehearse the combined map, evidence and model-output flow | One success and one limitation; a clearly labeled replay/recording if live inference fails |

## Training-owner handoff contract — done

Every run is under its own folder in `artifacts/nebius/` (`all-sources`,
`ablation-{acled,chirps,wfp,portwatch}`, `pretrained-fulltest`), pulled from the HF mirror's
`gpu-results/` tree: `run.json`, `losses.json`, `fine_tuned.jsonl`, `fine_tuned-metrics.json`,
`benchmark.md`, and `best_model.pt` (all-sources only; SHA-256
`a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10`, not in the original
manifest so recorded fresh here). `pretrained-fulltest/` is the untouched-checkpoint
baseline on the full 2,230-example test set — `pretrained.jsonl` + `pretrained-metrics.json`,
merged from 8 parallel sharded jobs (`src/open_relief/pretrained_eval.py`); see
[FINDING-pretrained-baseline.md](FINDING-pretrained-baseline.md). These files are gitignored;
re-fetch with `huggingface_hub.hf_hub_download('Alaeddinnn/OpenRelief', ..., repo_type='dataset')`.

**The submitted checkpoint is the 2,781-example all-sources run** (`gpu-run-2781` /
`open-relief-train-2781`), not the two separate 9,065-example runs that were still
training at submission time — resolves the prior training-cohort ambiguity. The
checkpoint supports `recommended_actions`: see the predictions in
`frontend/src/data/live-predictions.json`. `pretrained.jsonl`/`pretrained-metrics.json`
do not exist for any run (all launched with `--skip-pretrain-eval`); no
before/after-fine-tuning table is claimed.

## Inference endpoint, the static snapshot, and live chat

`src/open_relief/serve.py` loads the checkpoint and reuses `adapter.format_input` +
`evaluate.parse_prediction` (the exact code path used for the reported benchmark numbers),
deployed as a Nebius **AI endpoint** (`open-relief-endpoint`, `gpu-rtx6000-a`,
`project-e05dv2fbln000444nt4bbz`) exposing `GET /countries` and `GET /predict?iso3=XXX`,
kept running so the chat panel can call it live.

The **map** does not call this endpoint at runtime — `scripts/generate_live_predictions.py
<endpoint-url>` batch-generates one real forward pass per test-set country and writes
`frontend/src/data/live-predictions.json`, which the map reads directly and synchronously
(`frontend/src/lib/liveModel.js`), so it always renders instantly regardless of endpoint
uptime. Intended production cadence for this snapshot is a daily/weekly re-run against a
live cutoff, not per-request generation. The committed snapshot records its own
`generated_at` timestamp and checkpoint hash.

The **chat panel** (`ModelChat.jsx`) does call the endpoint live, once per question, for a
freshly-generated answer — falling back to the cached snapshot entry, then to the synthetic
demo answers, if the endpoint is unreachable. `frontend/.env.local`'s `VITE_INFERENCE_URL`
points at the endpoint's managed URL.

The default 256 test IDs have only one phase-4 example. Recomputed persistence scores
0.7276 macro-F1 and 0.7500 accuracy on those IDs. Match IDs before comparing with the
reported GPU numbers; show per-class support and deterioration precision/recall/F1.
Keep test-driven ablation exploration disclosed. See [readiness analysis](HACKATHON-READINESS.md).

## Documentation and artifact checks

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m open_relief.validate artifacts/multimodal \
  --annotations artifacts/annotations-training.jsonl \
  --output reports/pretraining-validation.json
.venv/bin/python scripts/build_annotation_showcase.py
git diff --check
```

Open `docs/examples/annotation-atlas/index.html` directly in a browser; no server or external
assets are required. GitHub renders its adjacent README and charts. The showcase examples
are training annotations generated previously through the LLM endpoint, not model forecasts.

`scripts/package_handoff.py` bundles code, docs, prepared data and available annotations.
It includes the frontend source and GPU Dockerfile but does not automatically include GPU checkpoints.
Deliver checkpoints explicitly and verify the final archive inventory. The frontend starts with
`cd frontend && npm ci && npm run dev`. `scripts/upload_to_nebius.sh` uploads the prepared
multimodal dataset only; required annotations must be transferred separately.

No new annotation job, cloud deployment or checkpoint publication is triggered by these
documentation/showcase commands. Resuming annotation is optional and belongs with the
training owner's decisions about time, budget and supervision coverage.
