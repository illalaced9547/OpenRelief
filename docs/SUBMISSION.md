# Submission checklist and ownership

The challenge slides require a working demo, code with training configuration, a checkpoint
or adapter, dataset documentation, and a short held-out evaluation against a baseline.
The completed frontend is now in `frontend/`; it still uses synthetic fixtures until model integration.
Training, checkpoint delivery and final evaluation are owned by the training model/workstream.

| Deliverable | Owner / remaining action | Acceptance check |
|---|---|---|
| World-map demo | **Done for the chat panel**: `ModelChat.jsx` calls the live checkpoint for the 14 test-set countries via `VITE_INFERENCE_URL`, falls back to synthetic fixtures otherwise. The map's risk-%/price/confidence cards remain illustrative (no natural mapping from categorical IPC phase to those numeric fixtures in the time available) | Works after a fresh start; live vs demo answers are labeled per-message in the chat |
| Annotation demonstration | Documentation workstream: charted training examples and cached generated arguments | [Atlas](examples/annotation-atlas/README.md) and offline HTML load; exact examples and request hashes included |
| Code and configuration | All owners: record submitted commit and checkpoint's actual code version | README command matches the delivered configuration; no conflict markers or credentials |
| Checkpoint / adapter | **Done**: `best_model.pt` retrieved to `artifacts/nebius/all-sources/`, SHA-256 `a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10`; also loaded and serving live on Nebius (`open-relief-serve` job) | Loads in a fresh process (proven by the running live endpoint) and produces valid examples |
| Evaluation | **Done for the 256-example cohort** (see [FINDING-portwatch-signal.md](FINDING-portwatch-signal.md)); full-2,230 reruns were in flight at submission time, folded in only if they landed | Identical sample IDs for compared models, explicit split/class support and no unsupported causal claims |
| Dataset documentation | Documentation/data owners: dataset card, provenance, coverage; resolve HFID upstream terms | [Dataset card](DATASET_CARD.md) matches manifests; source access and reuse claims are accurate |
| Presentation / fallback | Team: rehearse the combined map, evidence and model-output flow | One success and one limitation; a clearly labeled replay/recording if live inference fails |

## Training-owner handoff contract — done

Every run is under its own folder in `artifacts/nebius/` (`all-sources`,
`ablation-{acled,chirps,wfp,portwatch}`), pulled from the HF mirror's `gpu-results/` tree:
`run.json`, `losses.json`, `fine_tuned.jsonl`, `fine_tuned-metrics.json`, `benchmark.md`,
and `best_model.pt` (all-sources only; SHA-256
`a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10`, not in the original
manifest so recorded fresh here). These files are gitignored; re-fetch with
`huggingface_hub.hf_hub_download('Alaeddinnn/OpenRelief', ..., repo_type='dataset')`.

**The submitted checkpoint is the 2,781-example all-sources run** (`gpu-run-2781` /
`open-relief-train-2781`), not the two separate 9,065-example runs that were still
training at submission time — resolves the prior training-cohort ambiguity. The
checkpoint supports `recommended_actions`: see live `/predict` responses.
`pretrained.jsonl`/`pretrained-metrics.json` do not exist for any run (all launched with
`--skip-pretrain-eval`); no before/after-fine-tuning table is claimed.

## Live inference endpoint

`src/open_relief/serve.py` loads the same checkpoint and reuses `adapter.format_input` +
`evaluate.parse_prediction` (the exact code path used for the reported benchmark numbers),
deployed as a Nebius **AI endpoint** (`open-relief-endpoint`, `gpu-rtx6000-a`,
`project-e05dv2fbln000444nt4bbz` — `nebius ai endpoint create`, not `job create`: jobs only
expose a private VPC-internal address, endpoints get a public managed `https://` URL)
exposing `GET /countries` and `GET /predict?iso3=XXX`. It runs real-time generation against
stored test-partition examples (not arbitrary free-form dates — the model needs the
prepared multivariate window). `frontend/.env.local`'s `VITE_INFERENCE_URL` is set to the
endpoint's managed URL; unset, the chat automatically falls back to the synthetic fixtures.

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
