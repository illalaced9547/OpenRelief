# Open Relief status — 13 September 2026

The frontend is now in `frontend/`; data preparation and native TimeNet connectors are
implemented; 2,781 training annotations are available. Nebius training/ablation results
are reported in the repository, and the training owner is handling the final checkpoint
and evaluation. The frontend still uses synthetic fixtures until model integration.

| Area | Current evidence |
|---|---|
| Dataset | Version `8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3`; 9,065 train / 2,503 validation / 2,230 test; 21 channels |
| Validation | Dataset integrity and temporal checks pass; all 2,781 supplied training annotations pass the current schema validator |
| Annotation | 30.68% coverage, not complete; six-example current pilot also includes actions; prior pre-action artifacts are obsolete |
| Connectors | Four native TimeNet connectors with tested TimeF round trips; not registered upstream |
| Frontend | World map, methodology, country detail panels and demo chat; synthetic values and explanations; [setup](../frontend/README.md) |
| Training | [Exploratory remote report](FINDING-portwatch-signal.md); exact artifacts and cohort still need reconciliation by training owner |
| Presentation | [Annotation atlas](examples/annotation-atlas/README.md): three training cases, source graphs, unedited generated arguments and offline HTML |
| Tests | 25 passing at the readiness check; rerun after changes using the README command |

## Measured local baseline

| Persistence cohort | Macro-F1 over present classes | Accuracy | Deterioration F1 |
|---|---:|---:|---:|
| Current runner's default 256 test IDs | 0.7276 | 0.7500 | 0.000 |
| Full test, 2,230 examples | 0.7350 | 0.7744 | 0.000 |

The default subset has one phase-4 example; the full test has five. Neither has phase-5
examples. Match sample IDs before comparing these metrics with remote model results.
The remote all-sources report lists 0.7199 macro-F1 and 0.7344 accuracy; this is not evidence
of improvement over persistence if its IDs match the default cohort. The no-shipping run
reports lower macro-F1 but higher accuracy/deterioration F1, so interpretation is metric-dependent.
See [audit evidence](../reports/hackathon-readiness-audit.json) and [analysis](HACKATHON-READINESS.md).

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

Training owner: final checkpoint, inference contract, exact run provenance, matching-cohort
metrics and generated explanation/action review. Frontend owner: replace synthetic fixtures
with supported outputs; country risk percentages and alternate horizons are not research
model outputs. Documentation workstream: consistent README, dataset card, charts, annotation
gallery and submission checklist. Team: verify links, load the checkpoint, rehearse a live
demo and retain a clearly labeled fallback.

The dataset remains retrospective with assumed release lags; national covariates do not
prove district exposure. FCS/rCSI normalization direction is undocumented. Source ablations
are associative and may retain language references to removed inputs. Full details and
source terms are in [the dataset card](DATASET_CARD.md) and [source inventory](SOURCES.md).

[Current plan](PLAN.md) · [Submission checklist](SUBMISSION.md)
