# Execution decisions and remaining sequence

User-confirmed scope: IPC phase at t+3 months primary, deterioration secondary; six monthly
history points; plain month-of-year series; multinational chronological training; official
TimeNet connectors; local annotation within $200; training on a separate GPU machine with
$1,000 available. The full annotation run is explicitly deferred until later on this machine.

Completed locally:

1. Inspected HFID, HANDOFF.md, official source APIs, OpenTSLM SP/Flamingo and actual TimeNet.
2. Acquired national PortWatch, ACLED, WFP and CHIRPS data and aligned them with HFID.
3. Built six-month district examples, changed the training freeze to December 2022,
   purged crossing labels, and added existing-data-only derived channels and monthly IPC history.
4. Implemented independently reusable acquisition and native TimeNet connectors with raw
   provenance, cache verification, TimeF writing and verified round trips.
5. Implemented strict, cached, budget-controlled official OpenAI annotation and tested a pilot.
6. Implemented native OpenTSLM input/training adapters, remote CUDA training and same-cohort
   before/after evaluation; prepared compatibility pins and setup/run scripts.
7. Ran local temporal/integrity checks, classical baselines and validation ablations; generated
   two dated case-study plots and a portable handoff package.

Remaining, in order:

1. Later here: run `bash scripts/annotate_local.sh full`; review annotations and verify full
   training coverage. The budget guard can stop early; its manifest reports incomplete coverage.
2. Package again and transfer to the GPU machine. Configure Hugging Face backbone access.
3. Run CUDA setup, pretrained evaluation, fine-tuning and held-out evaluation. These have not
   run locally and no OpenTSLM performance improvement is claimed.
4. Audit generated explanations independently against input values, provenance and uncertainty;
   attach actual predictions to the case-study plots. Compare source ablations on validation
   before choosing a final model, and reserve test data for the final comparison.

Optional future research: longer-window comparison, district weather/conflict aggregation,
relaxing mandatory FCS/rCSI coverage with explicit masks, seasonal anomalies, geographic
holdout, rolling-origin validation and uncertainty intervals accounting for country/time clusters.
