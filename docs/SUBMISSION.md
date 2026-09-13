# Submission checklist and ownership

The challenge slides require a working demo, code with training configuration, a checkpoint
or adapter, dataset documentation, and a short held-out evaluation against a baseline.
The completed frontend is now in `frontend/`; it still uses synthetic fixtures until model integration.
Training, checkpoint delivery and final evaluation are owned by the training model/workstream.

| Deliverable | Owner / remaining action | Acceptance check |
|---|---|---|
| World-map demo | Frontend/training owners: connect actual outputs; setup and preview URL are in frontend/README.md | Works after a fresh start; model outputs and observed outcomes are clearly distinguished |
| Annotation demonstration | Documentation workstream: charted training examples and cached generated arguments | [Atlas](examples/annotation-atlas/README.md) and offline HTML load; exact examples and request hashes included |
| Code and configuration | All owners: record submitted commit and checkpoint's actual code version | README command matches the delivered configuration; no conflict markers or credentials |
| Checkpoint / adapter | Training owner: supply artifact/link, hash, load instructions and actual trained schema | Loads in a fresh inference process and produces a valid example |
| Evaluation | Training owner: deliver raw predictions, manifests and final metric table | Identical sample IDs for compared models, explicit split/class support and no unsupported causal claims |
| Dataset documentation | Documentation/data owners: dataset card, provenance, coverage; resolve HFID upstream terms | [Dataset card](DATASET_CARD.md) matches manifests; source access and reuse claims are accurate |
| Presentation / fallback | Team: rehearse the combined map, evidence and model-output flow | One success and one limitation; a clearly labeled replay/recording if live inference fails |

## Training-owner handoff contract

Place each run under its own folder in `artifacts/nebius/` locally, or provide equivalent
download links. These files are ignored by Git and need separate delivery:

- `run.json`: exact dataset, IDs, checkpoint/backbone revisions, annotation hash, generation
  settings and training coverage; attach the launch command and code commit/patch.
- `fine_tuned.jsonl` and metrics, including sample IDs and raw generated text.
- `pretrained.jsonl` and metrics if presenting a before/after improvement.
- `losses.json`, `benchmark.md` and the final checkpoint/adapter with a SHA-256 digest.
- Matching manifests and predictions for source ablations, especially no-PortWatch.

Resolve whether the remote run trained on 2,781 records or all 9,065 with partial language
supervision. The current runner does the latter on the full prepared dataset. Confirm
whether the actual checkpoint supports `recommended_actions`. Do not silently substitute
teacher actions for checkpoint outputs in the frontend.

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
