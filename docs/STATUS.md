# OpenRelief status — 13 September 2026

The frontend is now in `frontend/`; data preparation and native TimeNet connectors are
implemented; 2,781 training annotations are available. **The fine-tuned checkpoint and its
evaluation artifacts have been retrieved and verified** (see [training loss curve](examples/training-loss-curve.png)
and [artifacts/nebius/](../artifacts/nebius/)). The checkpoint is deployed as a Nebius AI endpoint, kept running: the map reads a static
prediction snapshot (`frontend/src/data/live-predictions.json`) with no runtime network
dependency, while the chat panel calls the endpoint live per question and falls back to
that same snapshot, then to demo answers, if it's unreachable — see
[SUBMISSION.md](SUBMISSION.md) for the regeneration command.

| Area | Current evidence |
|---|---|
| Dataset | Version `8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3`; 9,065 train / 2,503 validation / 2,230 test; 21 channels |
| Validation | Dataset integrity and temporal checks pass; all 2,781 supplied training annotations pass the current schema validator |
| Annotation | 30.68% coverage, not complete; six-example current pilot also includes actions; prior pre-action artifacts are obsolete |
| Connectors | Four native TimeNet connectors with tested TimeF round trips; not registered upstream |
| Frontend | World map, methodology, country detail panels and chat; map/chat show the checkpoint's real batch-generated forecast for the 14 test-set countries, synthetic fixtures for the rest; [setup](../frontend/README.md) |
| Training | [PortWatch shipping finding](FINDING-portwatch-signal.md); checkpoint = 2,781-example all-sources run, retrieved to [artifacts/nebius/all-sources/](../artifacts/nebius/all-sources/), SHA-256 `a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10` |
| Presentation | [Annotation atlas](examples/annotation-atlas/README.md): three training cases, source graphs, unedited generated arguments and offline HTML |
| Tests | 25 passing at the readiness check; rerun after changes using the README command |

## Measured local baseline

| Persistence cohort | Macro-F1 over present classes | Accuracy | Deterioration F1 |
|---|---:|---:|---:|
| Current runner's default 256 test IDs | 0.7276 | 0.7500 | 0.000 |
| Full test, 2,230 examples | 0.7350 | 0.7744 | 0.000 |
| **Pretrained OpenTSLM-SP, no fine-tuning, full 2,230 examples** | **0.0** | **0.0** | 0.0 (invalid output rate 100%) |

The default subset has one phase-4 example; the full test has five. Neither has phase-5
examples. The remote all-sources report lists 0.7199 macro-F1 and 0.7344 accuracy on the
default cohort, in the same range as persistence there; the standout results are the
PortWatch ablation signal and the pretrained-vs-fine-tuned gap on the full test set (see
[FINDING-portwatch-signal.md](FINDING-portwatch-signal.md) and
[FINDING-pretrained-baseline.md](FINDING-pretrained-baseline.md)).

## Annotation and training semantics

Cached annotations use `gpt-5.6-terra`, objective labels and strict structured output.
They include precursor patterns, cross-domain hypotheses, rationale, driver-cited proposed
actions, uncertainty and annotation-quality confidence. They are retrospective teacher
supervision; future outcomes are never forecasting inputs. Current training answers retain
phase, rationale and action strings, while richer provenance stays in the annotation file.

The full annotation run was interrupted: 2,781/9,065 records exist. Its reconstructed
manifest reports approximately $89.85 accounted cache cost, not an API billing receipt.
Keep the cache and ledger to resume; the configured full-run ceiling is $185. This
submission work does not resume the paid job, and complete annotation is not mandatory.

Current code requires a nonempty matching annotation file and accepts partial coverage.
Unannotated examples train with empty rationale/action targets. The remote report describes
a 2,781-example slice; the training owner must reconcile that with the actual run.

Passing validation does not establish factual correctness. A separate citation-linkage
check found 44 actions across 41 annotations citing channels absent from earlier precursor
or interaction citations; this is not currently rejected by the validator. The atlas
preserves cached text, including limitations, rather than rewriting it into stronger claims.
The historical pilot review report predates the current action schema and full-run attempt.

## Remaining responsibilities

Training owner: done for this submission window — checkpoint retrieved and hashed, deployed
as a Nebius endpoint, and used to batch-generate the committed static prediction snapshot
consumed by the map and chat. Still open: the 5 full-2,230-example ablation reruns in
flight may or may not land before the deadline (see
[HACKATHON-READINESS.md](HACKATHON-READINESS.md)); fold in if they do. Frontend owner: for
the 14 checkpoint-evaluated countries the map's risk number is a direct linear mapping of
the real predicted IPC phase (not a calibrated probability), and the price/confidence cards
are replaced with the real cutoff/rationale/actions; every other country keeps the original
illustrative fixtures, clearly labeled MODEL FORECAST vs DEMO throughout. Documentation
workstream: consistent README, dataset card, charts, annotation gallery and submission
checklist. Team: verify links, rehearse a live demo and retain a clearly labeled fallback.

The dataset remains retrospective with assumed release lags; national covariates do not
prove district exposure. FCS/rCSI normalization direction is undocumented. Source ablations
are associative and may retain language references to removed inputs. Full details and
source terms are in [the dataset card](DATASET_CARD.md) and [source inventory](SOURCES.md).

[Current plan](PLAN.md) · [Submission checklist](SUBMISSION.md)
