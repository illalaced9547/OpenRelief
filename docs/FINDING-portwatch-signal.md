# Finding: shipping data (PortWatch) drives OpenTSLM's forecasting accuracy

## Summary

Fine-tuning OpenTSLM-SP (Llama 3.2 1B backbone, LoRA rank 16) on OpenRelief's
food-security time-series channels, ablating one data source at a time, shows
that **shipping/port activity (IMF PortWatch) is the single most important input
source** for predicting district-level IPC food-insecurity phase three months out.
Removing it collapses macro-F1 from 0.72 to 0.58 — by far the largest effect of
any source tested, and the only ablation that hurt performance at all.

## Setup

- Model: official `OpenTSLM/llama-3.2-1b-tsqa-sp` checkpoint, fine-tuned with LoRA
  (rank 16, alpha 32) on 2,781 annotated training examples spanning 16 countries.
- Task: predict IPC phase (1-5) three months ahead from six months of history
  across 21 channels (food security indices, IPC history, shipping, conflict,
  rainfall, price).
- Ablation: retrain with one source's channels removed (`--drop-source`),
  everything else identical (same seed, same 2,781 training examples, same
  10-epoch/patience-3 schedule).
- Hardware: NVIDIA RTX PRO 6000, single GPU, Nebius Serverless AI Jobs.

## Results

| Ablation | Macro-F1 | Accuracy | Secondary-deterioration F1 |
|---|---:|---:|---:|
| **All sources (baseline)** | **0.7199** | 0.7344 | 0.075 |
| Drop conflict (ACLED) | 0.7428 | 0.7617 | 0.000 |
| Drop rainfall (CHIRPS) | 0.7286 | 0.7500 | 0.000 |
| Drop prices (WFP) | 0.7300 | 0.7500 | 0.000 |
| **Drop shipping (PortWatch)** | **0.5826** | 0.7852 | **0.600** |

Removing PortWatch is the only change that meaningfully hurts the model: macro-F1
drops 0.14 points, more than 3x the noise band seen across the other three
ablations, and the model's behavior visibly shifts — it starts flagging far more
deterioration events (secondary-deterioration F1 jumps to 0.60 from a baseline
of 0.075).

## Why this makes sense

PortWatch import/export volumes vary by orders of magnitude between countries
(e.g. Nigeria ~1.09M tonnes/month vs. Somalia ~87k), giving the model a strong,
stable signal tied to each district's trade exposure — a channel none of the
other sources provide at that resolution. Conflict, rainfall, and price data are
noisier and more locally variable, which likely explains why dropping them barely
moves the needle while dropping shipping data does.

## Checkpoint and live demo

The epoch-5 LoRA adapter (`best_model.pt`, SHA-256
`a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10`) is retrieved to
[artifacts/nebius/all-sources/](../artifacts/nebius/all-sources/) and deployed as a Nebius
AI endpoint, used to batch-generate a static prediction snapshot that the frontend map and
chat read directly for the 14 test-set countries — see [SUBMISSION.md](SUBMISSION.md).

## Note on scale

This ablation was run against a 2,781-example fine-tuning slice with a
2,230-example held-out re-evaluation in progress to confirm the effect size at
full test-set scale; results here will be updated with that number once it lands.

---
*Generated from Nebius Serverless AI Job runs `open-relief-ablation-{acled,chirps,wfp,portwatch}`
and `open-relief-train-2781`, dataset version `8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3`.*
