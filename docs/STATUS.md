# Open Relief status — 12 September 2026

**Local preparation is implemented. Full annotation is deliberately deferred until later
on this machine; GPU training and the OpenTSLM before/after comparison remain pending.**

## Dataset and added features

Final dataset version:
`8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3`.

- Primary target: district FEWS IPC phase at cutoff +3 months; secondary deterioration:
  at least one phase increase over the latest available assessment, no older than six months.
- Six monthly history points; month of year remains a single integer 1–12 series.
- Training: 9,065 examples across 16 countries. Validation: 2,503 across 16. Test: 2,230
  across 14. No eligible Yemen or Ethiopia test examples under the selected dates.
- Added ten channels without additional downloads: monthly known IPC and assessment age;
  price changes at one/three months; FCS/rCSI differences at one/three months; trailing
  three-month conflict events; cargo imports versus their prior three-month mean.
- Total: 21 channels plus observation masks. Changes retain their source prefix for ablations.
- Rebuilt price selection excludes milling services and matches actual staple commodities.
  Yemen's selected series is imported rice, with exact package unit retained.

Checksums, temporal splits, input availability, channel shapes, calendar values and
annotation alignment are checked by `open_relief.validate`. See
[the current validation report](../reports/dataset-validation.json).
Missing covariates and initial rolling-window entries remain null, not zero observations.
Price coverage is 73%, shipping 79%, conflict 100%, rainfall 83% after assumed lag masking.

## Annotation pipeline

The final local suite passes 19 tests, including temporal leakage, derived-feature missingness,
IPC assessment chronology, budget accounting and native TimeF serialization.

Six-example live pilots use `gpt-5.6-terra` and the official OpenAI API. The final selection
covers six countries and includes improvement, deterioration and stable outcomes. JSON
schema validation and exact objective-label preservation pass. Full training annotations
have **not** been generated. The final pilot output and request usage are in
`artifacts/annotations-final-pilot.jsonl` and its adjacent manifest.

Manual review identified a confusion between the age of a rolling IPC record and the
newer assessment available at the forecast cutoff. The request now explicitly includes
both assessment timelines and the separately computed cutoff age. This is covered by a
regression test. The rerun correctly identifies the June Hajr assessment as one month old
at the July cutoff. Schema validity alone is not treated as factual correctness.

Cache replay is tested with an API stub that raises if any network request is attempted.
Requests, raw responses and validated outputs are cached. A persistent spend ledger keeps
conservative reservations for ambiguous failures, and a process lock prevents concurrent
runs from sharing the budget. Keep the cache to resume later. Output manifests distinguish
prior accounted spend from new-run estimates; these are estimates, not billing receipts.
The final six-example pilot has a conservative usage estimate of $0.125. Its cache replay
cost $0 in new API calls. The retained response/charge ledger accounts for about $0.447
across saved pilot requests; older pre-ledger failed attempts are not represented.

Later, run:

```sh
bash scripts/annotate_local.sh full
```

This requests all training examples, eight workers, with a conservative $185 accounting
ceiling. If the guard stops early or any request fails, completed annotations remain
cached and the manifest reports the incomplete result. Do not bypass the budget guard.
GPU rationale training requires complete, version-matched annotations and rejects a pilot
file. See the README for the completeness check and subsequent transfer commands.

## Reusable TimeNet connectors

Native PortWatch, ACLED, WFP and CHIRPS connectors implement the official TimeNet
BaseConnector contract, pinned to commit `c39ca32b64ad0c89ea54093dbcb285c1a93eb006`.
All four have verified TimeF write/read round trips using a Yemen January–March 2020
example. Calendar timestamps, null values, units and provenance survive the conversion.

The acquisition project is independently installable and can be extracted as a repository.
It is not yet published to an upstream registry. See
[connector documentation](../open-relief-data/README.md).

## Measured local baselines

Test-set results (2,230 examples; macro-F1 across classes present):

| Model | Macro-F1 | Accuracy |
|---|---:|---:|
| Training majority | 0.0752 | 0.1771 |
| Latest available IPC, majority fallback when absent | 0.7350 | 0.7744 |

Persistence issues no deterioration alerts on examples with a known baseline, so its
secondary deterioration recall is zero despite its strong phase accuracy.

Classical logistic-regression ablations use the **validation** partition (2,503 examples),
with preprocessing fitted on training only:

| Features | Macro-F1 | Accuracy |
|---|---:|---:|
| All sources | 0.5844 | 0.7000 |
| Food history and calendar only | 0.6032 | 0.7339 |
| Without shipping | 0.5927 | 0.7036 |
| Without conflict | 0.5113 | 0.6304 |
| Without rainfall | 0.5615 | 0.6772 |
| Without prices | 0.6104 | 0.7315 |

Food history includes IPC history and the derived FCS/rCSI channels. These results suggest
some sources matter conditionally in this baseline, but do **not** demonstrate that adding
all sources improves overall forecasting. They measure association, not causal effects.
Test baselines and validation ablations have different cohorts and should not be directly
compared. Detailed files are under `artifacts/evaluation` and `artifacts/ablations`.

## GPU handoff and remaining work

Official OpenTSLM input adapters and a CUDA runner are implemented, with source/dependency
pins, resolved checkpoint hashes, LoRA, early stopping, raw predictions, country metrics
and same-cohort before/after evaluation. GPU execution has not been performed or validated
here. The default comparison uses 256 held-out examples; the CLI can evaluate all examples.

Two dated input case-study plots are available in `artifacts/demo-final`; they explicitly
mark model forecasts as pending. After GPU training, attach actual generated predictions
and review explanations separately for numerical accuracy, scope and uncertainty.

`bash scripts/setup_gpu.sh` and `bash scripts/train_gpu.sh` are the remote entry points.
The package script creates `artifacts/open-relief-handoff.tar.gz`, excluding credentials,
virtual environments and raw caches. Repackage after full annotation to include its output.

Remaining: full local annotation and quality review; GPU setup/access validation;
pretrained OpenTSLM evaluation; fine-tuning; held-out comparison and explanation evaluation.
No training, deployment or publication is claimed complete.
