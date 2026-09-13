# Finding: fine-tuning is not optional — the untouched checkpoint fails outright

## Summary

The official, untouched `OpenTSLM/llama-3.2-1b-tsqa-sp` checkpoint was evaluated on the
**full 2,230-example test partition** with no fine-tuning at all (no LoRA, no training
steps — exactly the checkpoint as published). It produced **zero valid predictions**:
every one of the 2,230 outputs failed to parse as the required `{"phase": int,
"rationale": str, ...}` JSON. Macro-F1, accuracy and recall are therefore all 0.0 by
definition of `invalid_rate = 1.0`.

## Setup

- Model: official `OpenTSLM/llama-3.2-1b-tsqa-sp` checkpoint, **no LoRA adapter loaded**.
- Evaluated on all 2,230 test examples (not a subset) — same prompts
  (`src/open_relief/adapter.py:format_input`), same parser
  (`src/open_relief/evaluate.py:parse_prediction`), same generation settings
  (`max_new_tokens=256, do_sample=False`) used everywhere else in this repo.
- Run sharded across 8 parallel Nebius jobs (`src/open_relief/pretrained_eval.py`,
  `--shard-index/--shard-count`) to fit the full test set in ~20 minutes instead of
  ~2.5 hours sequential; merged and re-scored locally with the same `evaluate.score`
  function used for every other reported number. Raw outputs and metrics:
  `artifacts/nebius/pretrained-fulltest/`.

## Result

| Model | Cohort | Valid output rate | Accuracy | Macro-F1 |
|---|---|---:|---:|---:|
| **Pretrained checkpoint (no fine-tuning)** | Full test, 2,230 | **0%** | 0.0 | 0.0 |
| Fine-tuned (all-sources) | 256-example cohort | **100%** | 0.7344 | 0.7199 |
| Persistence (last known phase) | Full test, 2,230 | n/a | 0.7744 | 0.7350 |

Inspecting the raw pretrained output confirms this is a real capability gap, not a
scoring bug: the untouched checkpoint does not attempt the requested JSON at all — it
continues echoing fragments of the input prompt's own text (e.g. repeating the literal
string `"0=missing."` from the channel-description text, then trailing off into repeated
numeric tokens). It was never exposed to this task's instruction/output format, so it has
no basis to imitate it. Fine-tuning is what makes the model attempt the task at all, let
alone competitively with the persistence baseline.

## Verification: ruling out a pipeline bug

The near-identical output across different countries under greedy decoding was flagged
as suspicious and checked directly (`src/open_relief/pretrained_probe.py`, run locally on
an idle RTX 3090 for a quick turnaround). Four variants tried on the same 6 examples:

| Variant | Result |
|---|---|
| Greedy (as reported above) | Identical degenerate loop regardless of country/input |
| Sampled (temperature 0.8) | **Output now varies per example** — confirms the model is conditioning on the real input — but is pure gibberish, no JSON structure |
| Few-shot (a worked JSON example prepended to the prompt) | No change; still degenerates identically |
| Forced JSON prefix (generation seeded with `{"phase":`) | Still collapses into the same nonsense immediately after |

The sampled variant proves the input genuinely reaches the model (different countries
produce different sampled continuations); the fact that none of the other three
interventions — including literally showing it the target format — produces anything
resembling `{"phase": N, "rationale": ...}` rules out a prompt-construction or generation
bug. This is the same conclusion as the greedy-only result, now on firmer ground.

## Caveat

This baseline and the fine-tuned row above are **not on the same cohort size** (2,230 vs
256) — the fine-tuned model's own full-2,230 numbers were still computing via a separate
in-flight rerun as of this writing.
The comparison that matters here is qualitative and overwhelming regardless of cohort
size, though: a 0% valid-output rate cannot improve with a larger sample, so the
core conclusion — pretrained fails outright, fine-tuning is necessary — does not depend
on matching cohorts to hold.

---
*Generated from Nebius Serverless AI Jobs `pretrained-eval-shard-{0..7}`, dataset version
`8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3`.*
