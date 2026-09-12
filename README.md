# Open Relief

Predict district-level **FEWS NET IPC phase three months ahead** from six months of
monthly food-security, shipping, conflict, rainfall and food-price histories. Deterioration
(an increase of at least one IPC phase) is a secondary analysis. Official OpenTSLM is the
primary model; simple classical models are comparison baselines.

Local data preparation and native TimeNet connectors are implemented. Annotation has been
tested with a small live pilot; **full annotation runs later on this machine**, followed
by fine-tuning on a separate CUDA machine. See [current status](docs/STATUS.md) for measured
results and remaining work. No OpenTSLM improvement has been measured yet.

## Current dataset

| Partition | Rule | Examples |
|---|---|---:|
| Training | Target plus assumed release lag available by December 2022 | 9,065 |
| Validation | January–July 2023 cutoffs, labels available by July 2023 | 2,503 |
| Test | August–December 2023 cutoffs, exact target at cutoff +3 months | 2,230 |

Labels that cross the training or validation freeze are purged. The eligible validation
cutoffs therefore end in March 2023. Training spans 16 countries; test has 14, with no
eligible Yemen or Ethiopia examples. These are country-imbalanced retrospective samples,
not independent crisis events. Six complete monthly FCS/rCSI observations remain required.

There are **21 monthly channels**, with an availability mask for each at model input:

- FCS/rCSI normalized indices, and the requested plain `month_of_year` integers 1–12.
- Last known IPC phase and assessment age, reconstructed as of each historical month.
- Four PortWatch measures, ACLED events/fatalities, CHIRPS rainfall, WFP staple price.
- One- and three-month price percentage changes and FCS/rCSI differences, trailing
  three-month conflict events, and cargo imports relative to the previous three months.

Derived series use only the existing six-point window. Early entries without enough
history remain null, as do ratios with nonpositive denominators. No new downloads were
needed for these features. Source prefixes are retained so an ablation removes both a
source and its derived features. IPC history expires after six months without an assessment.

All non-calendar series are scaled to [-1,1] within each input window, with original scale
statistics and units retained in text. Calendar scaling is fixed from 1–12; there are no
sine/cosine channels. The official patch-size-4 collator pads six observations to eight
positions. Padding is a model operation, not extra observed months.

## Local setup and rebuilding

Use Python 3.12 for the complete TimeNet workflow:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-local.lock.txt
.venv/bin/python -m pytest -q
bash scripts/rebuild_local.sh
```

`rebuild_local.sh` uses the already downloaded monthly artifacts and original HFID CSV.
It makes no API calls. To acquire fresh data, follow
[the separate acquisition project](open-relief-data/README.md). A fresh acquisition produces
three all-country monthly files; supply those three to `open_relief.enrich` instead of
mixing them with overlapping country-extension files from this workspace.

Inputs, objective targets, manifests and annotations are separate artifacts. Dataset
loading verifies checksums. `reports/dataset-validation.json` records sample counts,
country coverage, channel missingness and temporal checks.

## Annotation: test now, full run later here

Keep the official OpenAI API key in `.env`, following `.env.example`; never include it in
a handoff. The selected model is `gpt-5.6-terra`. It receives training records and their
objective future phase, using strict JSON output. Recalled context and inference are
separated from observed evidence; retrieved evidence is disabled unless actually supplied.
Annotations are retrospective supervision and never become inference inputs.

```sh
# Small diverse live test; not the full training set.
bash scripts/annotate_local.sh pilot

# Run later, on this machine, when ready to prepare all fine-tuning supervision.
bash scripts/annotate_local.sh full

# Verify full coverage before transferring it to the training machine.
.venv/bin/python -m open_relief.validate artifacts/multimodal \
  --annotations artifacts/annotations-training.jsonl --require-complete-annotations \
  --output reports/pretraining-validation.json
```

The full command selects all 9,065 training examples, uses eight workers, and stops before
a conservative $185 cache-wide accounting ceiling. It may finish fewer examples if that
ceiling is reached; check the output manifest. Keep `artifacts/annotation-cache` between
runs. Exact requests reuse cached responses, including after validation fixes. Budget
reservations persist for ambiguous API failures; automatic API retries are disabled.
Only one annotation process may own the cache at a time. Do not delete the cache to reset
spend accounting. Other API projects and old pre-ledger attempts are outside this ledger;
the margin below the user's $200 budget is intentional.

Validated schema and unchanged labels do not guarantee every explanation is factually
correct. Review numeric claims, assessment dates, national/local scope and causal language
on a sample before treating rationales as high-quality supervision. `confidence` is an
annotation-quality judgment, not calibrated forecast probability.

## GPU fine-tuning later

The runner imports official OpenTSLM at commit
`2968f4b891baab4307f7e9d0043e87677b593a30`. It defaults to the official Llama 3.2 1B TSQA
SP checkpoint and records resolved checkpoint/backbone revisions and hashes. SP is the
initial practical choice, not an empirically established winner. The runner also supports
the official corresponding Flamingo checkpoint.

On a Linux CUDA machine, with Hugging Face access to Llama 3.2 1B configured:

```sh
bash scripts/setup_gpu.sh
bash scripts/train_gpu.sh artifacts/gpu-run
```

The training script requires complete annotations. It first evaluates pretrained OpenTSLM,
then fine-tunes and evaluates the same 256 deterministically selected test IDs. Use a fresh
output directory per run. The direct CLI accepts `--eval-limit 100000` for the full held-out
partitions and `--checkpoint OpenTSLM/llama-3.2-1b-tsqa-flamingo` for the alternative.
For a phase-only comparison, invoke `python -m open_relief.gpu artifacts/multimodal` without
`--annotations`; the rationale target is then empty and explanation learning is not tested.

Training uses official architecture, collator, loss, LoRA and checkpoint methods, with
batch size one and gradient accumulation eight, maximum ten epochs, and patience three.
Validation uses phase JSON prefix loss, excluding retrospective rationale text. Outputs
include pretrained/fine-tuned raw predictions, country metrics, losses, checkpoint and a
before/after table. Generation validity is scored separately. GPU dependencies are pinned
from inspected upstream versions; CUDA execution remains to be tested on that machine.

## Evaluation, plots and transfer

```sh
.venv/bin/python -m open_relief.evaluate artifacts/multimodal
.venv/bin/python -m open_relief.ablation artifacts/multimodal --split validation
.venv/bin/python -m open_relief.demo artifacts/multimodal --output artifacts/demo-final
.venv/bin/python scripts/package_handoff.py
```

After training, pass `--predictions artifacts/gpu-run/fine_tuned.jsonl` to the demo command.
Without predictions, the two plots explicitly show input case studies with GPU forecasts
pending. They are selected by historical worsening, not prediction correctness.
The transfer archive includes code, prepared data and available annotations; it excludes
`.env`, virtual environments, raw download caches and obsolete pilots. Run packaging again
after the full annotation job to include its training JSONL and manifest.

## Material limitations

Historical release timestamps and revisions are unavailable: HFID, PortWatch, ACLED and
WFP use an assumed one-month lag; CHIRPS uses two. This is a retrospective research
benchmark, not proof of real-time forecasting performance. Country-level external signals
are shared by districts; country-average rainfall is not district exposure. Shipping is
not food-specific, food prices depend on changing market composition, and FCS/rCSI
normalization direction is undocumented. Price coverage is about 73%, shipping 79%,
conflict 100%, rainfall 83% after lag masking. No missing observation becomes a real zero.

Classical ablations measure association rather than causation. Do not equate a three-month
forecast horizon with demonstrated warning lead time or claim additional data improve
forecasts until held-out experiments support it. Source terms and provenance are in
[the source inventory](docs/SOURCES.md) and acquisition manifests.
