# Submission plan and workstream ownership

Updated 13 September 2026 after the frontend arrived at remote commit `22d2546`.
The team has approximately four hours in the submission window described during the review.
The frontend is implemented and checked into `frontend/`. The training model/workstream
owns training, checkpoint delivery and final evaluation. This workstream owns documentation,
annotation examples and a consistent presentation of the work.

| Workstream | State | Next action / completion criterion |
|---|---|---|
| Frontend | React world-map interface, methodology and local demo chat now in the repo | Frontend/training owners connect real outputs; synthetic country probabilities and horizon adjustments remain clearly labeled until then |
| Training and evaluation | **Done**: checkpoint retrieved+hashed, deployed as a Nebius endpoint, batch-generated forecast committed as static data for map/chat | See [SUBMISSION.md](SUBMISSION.md) training-owner handoff section for artifact paths, hash and regeneration command |
| Repository documentation | README, status, dataset card and submission checklist updated | Final training owner fills in verified results and links without overwriting input/annotation provenance |
| Annotation showcase | Three real training examples, charts, verbatim generated arguments, exact JSON and offline HTML | Review rendered examples and keep their distinction from fine-tuned forecasts visible |
| Visual consistency | Atlas and pipeline diagram use frontend charcoal/gray cards, thin connectors, Manrope and DM Sans | Check desktop/mobile gallery rendering; fonts bundled with licenses for offline viewing |
| Final submission | Checklist in SUBMISSION.md | Combine map demo, actual inference/results, checkpoint, code/configuration and dataset documentation; rehearse and verify links |

## Focus for this checkout

1. Pull and preserve all frontend work; inspect its actual visual system.
2. Explain the project and current evidence in the README, with quick links to frontend
   setup, dataset documentation and reproducible annotation examples.
3. Render existing cached LLM responses into compelling source-data charts and an argument
   gallery. Use no new annotation API calls. Include deterioration, persistent crisis and
   improvement; state that the future label was supplied to the training teacher.
4. Match charts, gallery and the pipeline diagram to the frontend design. Preserve original
   source values, missingness, channel references and uncertainty.
5. Validate the local suite, frontend build, example integrity and visual output; commit
   and push the documentation/showcase and preserved local changes.

## Training-owner handoff — done

The submitted checkpoint is the 2,781-example all-sources run (`gpu-run-2781`), not the
separate full-9,065-example runs, which resolves the earlier cohort ambiguity. It supports
`recommended_actions`. `run.json`, raw predictions, metrics, losses and the checkpoint
(SHA-256 `a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10`) are in
`artifacts/nebius/`; see [SUBMISSION.md](SUBMISSION.md). Persistence-vs-model comparison on
identical 256-example IDs, class support and the single-phase-4-example caveat are recorded
in [HACKATHON-READINESS.md](HACKATHON-READINESS.md) and [FINDING-portwatch-signal.md](FINDING-portwatch-signal.md).

The frontend currently displays synthetic country-level risk percentages over 30/90/180
calendar-day demo horizons; the research model predicts district IPC phase at three
calendar months. Decide the actual geography/horizon contract and display format. Do not
convert an IPC integer or annotation-quality confidence into an uncalibrated risk percentage.
Do not silently replace model explanations with teacher annotations.

## Defer

Completing all annotations, new acquisitions, a larger model, extensive hyperparameter
searches and a general data-discovery agent are not prerequisites for the submission.
The training owner decides whether any corrective run fits the remaining time. The frontend
already exists and does not need to be rebuilt by this workstream.

[Submission checklist](SUBMISSION.md) · [Current status](STATUS.md) ·
[Detailed readiness findings](HACKATHON-READINESS.md) ·
[Annotation atlas](examples/annotation-atlas/README.md)
