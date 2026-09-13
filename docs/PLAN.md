# Submission plan and workstream ownership

Updated 13 September 2026 after the frontend arrived at remote commit `22d2546`.
The team has approximately four hours in the submission window described during the review.
The frontend is implemented and checked into `frontend/`. The training model/workstream
owns training, checkpoint delivery and final evaluation. This workstream owns documentation,
annotation examples and a consistent presentation of the work.

| Workstream | State | Next action / completion criterion |
|---|---|---|
| Frontend | React world-map interface, methodology and local demo chat now in the repo | Frontend/training owners connect real outputs; synthetic country probabilities and horizon adjustments remain clearly labeled until then |
| Training and evaluation | Nebius runs reported; final artifacts managed by the training owner | Deliver checkpoint/hash, actual run configuration, raw predictions, same-ID baseline comparison and explanation samples |
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

## Training-owner handoff

The current full-dataset runner loads 9,065 training examples and accepts 2,781 annotated
records, using empty language targets for the remainder. The remote report instead refers
to a 2,781-example training slice; record the actual code/dataset used. Check whether the
submitted checkpoint includes the new recommended-action schema.

Deliver `run.json`, raw predictions, metrics, losses, exact command/code version and a
loadable checkpoint or adapter. Compare persistence on identical sample IDs. The default
256 test examples have only one phase-4 example; show class support and secondary
alert precision/recall/F1. Avoid broad causal claims from source ablations, particularly
while their retained language targets may mention removed input channels.

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
