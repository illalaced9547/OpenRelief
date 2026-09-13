# Open Relief dataset card

This retrospective research dataset pairs district food-security histories with national
context to study IPC phase forecasting and time-series-to-language supervision.

| Field | Value |
|---|---|
| Dataset version | `8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3` |
| Primary target | FEWS NET IPC phase at cutoff +3 calendar months |
| Secondary target | Any increase over the latest available IPC assessment, at most six months old |
| Inputs | Six monthly observations per channel; 21 channels plus separate observed-value masks |
| Geography | District targets and FCS/rCSI; external covariates aggregated to country |
| Training | 9,065 examples / 16 countries; target plus assumed release lag available by December 2022 |
| Validation | 2,503 examples / 16 countries; configured January–July 2023 cutoffs, eligible cutoffs end March after label purging |
| Test | 2,230 examples / 14 countries; August–December 2023 cutoffs, target exactly three months later |
| Test label support | Phase 1: 854; phase 2: 976; phase 3: 395; phase 4: 5; phase 5: 0 |
| Annotation coverage | 2,781 training records, 30.68%; cached structured LLM supervision |
| Prepared-data mirror | [Alaeddinnn/OpenRelief](https://huggingface.co/datasets/Alaeddinnn/OpenRelief) |

## Sources and measurement

HFID provides the original district panel, including FEWS IPC labels and normalized FCS/rCSI.
IMF PortWatch supplies national shipping totals, ACLED national conflict events/fatalities,
CHIRPS country-average rainfall and WFP national staple-price series with exact commodity
and package-unit metadata. See [source inventory](SOURCES.md), acquisition manifests and
[native connector cards](../open-relief-data/README.md) for URLs and provenance.

Historical publication timestamps and data revisions are unavailable. The benchmark assumes
one-month release lags for HFID, PortWatch, ACLED and WFP and two months for CHIRPS. It
therefore does not establish what could actually have been forecast in real time.

Ten channels derive IPC history/assessment age and price, food-index, conflict and shipping
changes from existing data. Calendar is a single month-of-year integer series. Derived
features use only the six-point window; insufficient histories remain null. IPC history is
reconstructed as of each historical month and expires after six months without an assessment.

Missing values remain null in the dataset. At model input they become zero placeholders
with separate masks, not observed zeros. Non-calendar channels are scaled within each
input window to [-1,1]; original scale statistics and units are retained in descriptions.
Calendar scaling is fixed to months 1–12. Model patch padding adds positions, not observations.

## Labels and annotations are separate

`inputs.jsonl`, `targets.jsonl` and the dataset manifest are independent from annotation
JSONL. Loaders verify dataset checksums. The annotation teacher receives the input and
objective future target, then generates precursor descriptions, cross-domain hypotheses,
a rationale, proposed actions, uncertainty and annotation-quality confidence. Strict
schema validation preserves the objective phase and checks channel references. Responses
are cached by request hash; a persistent budget ledger supports resumable annotation.

This is retrospective supervision, not independently observed expert reasoning. No retrieved
external evidence was supplied. Hypotheses may be wrong; confidence is not calibrated
forecast probability. An additional linkage audit found 44 actions across 41 annotations
whose driver list was not fully covered by earlier precursor/interaction citations, even
though the channel names passed the current validator. See [audit](../reports/hackathon-readiness-audit.json).

The [annotation atlas](examples/annotation-atlas/README.md) contains three actual annotated
training records selected for contrasting transitions and readable explanations. It is an
editorial illustration, not a representative quality estimate, test set or prediction demo.
Its machine-readable examples include all input channels, targets and unedited teacher text.

## Coverage and intended interpretation

Six complete FCS/rCSI observations are required. This excludes districts and periods with
missing core histories and produces country-imbalanced samples. Raw per-country window
counts for this six-month requirement are in
[`reports/hfid-audit-6months.json`](../reports/hfid-audit-6months.json); an earlier
twelve-month-window exploration is in [`reports/hfid-audit.json`](../reports/hfid-audit.json). Test has no eligible Yemen
or Ethiopia examples. After lag masking, approximate external coverage is 73% for prices,
79% shipping, 100% conflict and 83% rainfall. There are no phase-5 test examples and only
five phase-4 examples; do not describe this as demonstrated famine prediction.

National signals do not prove district exposure. Shipping totals are not food-specific;
rainfall averages do not measure local drought; prices depend on market composition.
The normalization direction of FCS/rCSI is undocumented, so numeric changes must not be
assigned raw-score severity interpretations. Overlapping district windows and shared
country signals create dependencies; country/time-aware uncertainty is preferable to
treating all records as independent events. Source ablations measure association.

## Access, reuse and reproducibility

Access to a source does not imply unrestricted redistribution. HFID's exact upstream
license/version must be documented by the data owner; none is inferred from the local CSV.
Retain IMF terms, ACLED TOU, WFP source metadata, CHIRPS attribution and geoBoundaries
attribution as applicable. TimeNet's code license does not license the underlying data.
The mirror and illustrative extracts are not an additional grant of source-data rights.

Configuration: [experiment.json](../configs/experiment.json). Validation:
[dataset report](../reports/dataset-validation.json). The full workflow and offline rebuild
commands are in [the README](../README.md). A fresh clone requires the prepared artifacts
or separately acquired source files; large caches and raw data are not tracked in Git.
