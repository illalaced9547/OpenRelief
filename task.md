You are an expert AI/ML engineer, time-series researcher, and systems architect. We are building a hackathon prototype called **Open Relief**.

Your job is to understand the project, inspect the available documentation and repository, resolve important ambiguities, create a concrete implementation plan, and then execute that plan step by step.

# 1. Project Goal

**Open Relief** is an early-warning system for predicting future deterioration in food security across countries and regions.

The core hypothesis is that changes in food insecurity can be predicted ahead of time by combining heterogeneous temporal signals such as:

* maritime trade and shipping activity;
* imports and exports;
* port activity;
* weather and rainfall;
* conflict and security incidents;
* other socioeconomic, logistics, climate, and crisis-related signals defined in `HANDOFF.md`.

`HANDOFF.md` is the authoritative project-level source for the datasets, target variables, terminology, geographic coverage, temporal resolutions, and known data sources.

**Read `HANDOFF.md` completely before proposing the final architecture. Do not invent replacements for datasets that the handbook already specifies unless there is a technical reason to do so.**

One important source is **IMF PortWatch**, which provides high-frequency maritime activity data derived from vessel movements and port activity. Use the official PortWatch platform/API and determine which specific datasets and endpoints are appropriate for this project.

The eventual product should be explainable as:

> **Open Relief is a multimodal time-series early-warning model that integrates trade, shipping, weather, conflict, and other signals to predict worsening food insecurity before it becomes visible in conventional lagging indicators.**

This is a hackathon prototype, so prioritize a technically credible, demonstrable, reproducible end-to-end system over unnecessary production complexity.

# 2. First Task: Understand the Existing Context

Before writing significant implementation code:

1. Read `HANDOFF.md` in full.
2. Inspect the existing repository, documentation, configuration, scripts, and datasets.
3. Identify every data source described in the handbook.
4. Identify the food-security target or index we are ultimately trying to predict.
5. Determine the available time range, temporal resolution, geographic resolution, and update frequency for each source.
6. Determine which parts of the system already exist and which must be built.
7. Inspect the official **OpenTSLM** implementation and documentation.
8. Verify any external framework, dataset, API, or library whose identity or usage is uncertain rather than guessing.

When something important is genuinely ambiguous, ask me targeted clarifying questions.

Group the important questions together rather than interrupting implementation repeatedly.

In particular, clarify anything that materially affects:

* the definition of the prediction target;
* forecast horizon;
* geographic unit;
* time resolution;
* train/validation/test periods;
* repository boundaries;
* OpenTSLM fine-tuning approach;
* data licensing or accessibility;
* compute constraints;
* hackathon demo requirements.

Do not ask questions whose answers can reasonably be obtained by reading the repository, `HANDOFF.md`, or authoritative documentation.

# 3. Proposed System Architecture

The project should be organized around several major components.

## A. Data Acquisition Repository

Create or design a **separate data-acquisition repository** responsible for retrieving and preparing the external datasets used by Open Relief.

This repository should contain:

* download scripts;
* API clients;
* scheduled-fetch scripts where appropriate;
* source-specific connectors;
* caching;
* validation;
* retries and error handling;
* raw-data versioning conventions;
* metadata describing provenance;
* timestamps indicating when data became available;
* standardized intermediate outputs.

Examples include the sources defined in `HANDOFF.md`, particularly maritime/trade signals from IMF PortWatch, rainfall/weather information, conflict or incident data, and any other relevant inputs.

The PortWatch integration should evaluate the appropriate official interfaces for retrieving the daily port activity, shipment, trade, import/export, or related maritime indicators required by the project.

Where possible, preserve both:

* `event_time`: when an observation actually occurred;
* `availability_time`: when that observation would realistically have become available to a forecaster.

This distinction will help prevent accidental look-ahead bias.

## B. Standardized Data Connector

The acquisition repository must expose a clean connector or adapter that converts the collected data into the standardized multivariate time-series representation expected by the Open Relief modeling pipeline.

Because this is a hackathon handoff, another team should be able to clone the repositories and understand:

* where the data comes from;
* how to fetch it;
* how it is transformed;
* how it becomes model input;
* which version of the data was used for experiments.

The handoff should not depend on undocumented local files.

# 4. Dataset Construction

Create a reproducible dataset-building pipeline that aligns heterogeneous data sources across:

* time;
* country/region;
* frequency;
* missing values;
* feature definitions.

Determine an appropriate canonical time frequency after inspecting the available sources.

Do not assume everything needs to be daily if another temporal resolution produces a more meaningful and reliable modeling task.

The pipeline should distinguish:

* raw observations;
* transformed features;
* prediction targets;
* metadata;
* training splits;
* optional LLM annotations.

Document all important:

* resampling;
* aggregation;
* interpolation;
* normalization;
* missing-data handling;
* feature transformations.

Never silently fill a historical input with information that would only have been known in the future.

# 5. Prediction Target

Determine the exact food-security outcome from `HANDOFF.md`.

Do not prematurely assume whether this is:

* binary classification;
* multiclass classification;
* ordinal classification;
* regression;
* change-point prediction;
* threshold-crossing prediction;
* natural-language prediction plus structured label;
* or some combination of these.

The primary task should represent something operationally meaningful, for example predicting whether food insecurity will significantly worsen within a future forecast horizon.

If the target definition is not sufficiently specified in the handbook, ask me before locking the modeling design.

The final target formulation should clearly specify:

* observation date;
* prediction cutoff;
* forecast horizon;
* geographic unit;
* definition of a worsening event;
* expected model output.

Because OpenTSLM is capable of generating language as well as reasoning over time-series signals, also evaluate whether the model should jointly produce:

1. a structured prediction; and
2. a concise natural-language rationale.

However, the quantitative prediction must remain measurable independently of the explanation.

# 6. LLM-Assisted Annotation Pipeline

Build a separate annotation component that communicates with an **OpenAI-compatible endpoint**.

For the prototype, use the official OpenAI API.

The objective is to enrich historical training examples with interpretations of how observed time-series patterns may relate to later changes in food security.

For a historical example, the annotation model may receive:

* historical multivariate time-series information;
* descriptions of the signals;
* the subsequent observed food-security outcome;
* relevant metadata;
* optionally retrieved historical context.

The annotation model should produce structured outputs describing things such as:

* whether a meaningful deterioration occurred;
* important precursor patterns;
* which variables changed;
* the temporal ordering of those changes;
* unusual or anomalous signals;
* plausible relationships between signals;
* relevant historical events;
* a concise explanation of the episode;
* confidence or uncertainty.

Use a strict JSON schema or another validated machine-readable output format whenever practical.

# 7. Using LLM Historical Knowledge

The annotation LLM **may use its internal historical knowledge** when that knowledge is useful.

For example, the model may already know that during a particular period a country experienced:

* a war;
* political instability;
* port disruption;
* drought;
* flooding;
* sanctions;
* a major economic shock;
* an agricultural crisis;
* a supply-chain disruption.

Do not artificially prevent the model from using this knowledge.

If the model is confident that a well-known historical event is relevant, it may include it as contextual information.

However, maintain reasonable provenance.

Where practical, distinguish between:

* **observed evidence** — directly present in our datasets;
* **retrieved evidence** — obtained from an external source;
* **model-recalled context** — supplied from the LLM's internal knowledge;
* **inference** — a relationship the model believes is plausible.

The purpose is not to prohibit model knowledge. The purpose is to avoid silently confusing an uncertain recollection with an observed fact.

For hackathon purposes, do not require external verification of every historical statement.

A sensible policy is:

* allow confident model knowledge;
* retrieve external evidence for important or uncertain claims when feasible;
* record uncertainty when the model is unsure;
* avoid treating speculative causal explanations as certain facts.

The annotation prompt should explicitly encourage the model to say when it is uncertain rather than hallucinating an explanation.

# 8. Prediction Labels vs. Explanatory Annotations

Keep the distinction between the objective target and the LLM-generated explanation clear.

For example:

### Ground-truth target

Derived from the actual future food-security index or other objective target defined in `HANDOFF.md`.

### Annotation

An LLM-generated interpretation describing what patterns or historical circumstances may have contributed to that target transition.

The LLM should therefore not arbitrarily decide the ground-truth outcome when an objective label can be computed from the actual food-security dataset.

Instead, the LLM enriches that label with temporal reasoning and context.

If there are cases where the food-security target itself requires interpretation, document exactly how the annotation model contributes to label generation.

# 9. Temporal Leakage and LLM Annotations

Temporal leakage must be handled carefully, but do not make the implementation unnecessarily restrictive.

For each training example, explicitly identify:

`INPUT WINDOW → PREDICTION CUTOFF → FUTURE TARGET WINDOW`

The forecasting input must only contain information that would have been available at the prediction cutoff.

However, during **training-data annotation**, the annotation model may inspect the future outcome because its role is to explain why that historical training example received its label.

For example:

`historical signals + known future deterioration → explanatory training annotation`

This can be legitimate supervision.

The critical question is whether information from the future subsequently leaks into something that the deployed model receives before making its prediction.

Therefore distinguish:

* input features;
* prediction labels;
* LLM-generated supervision;
* explanatory annotations;
* evaluation metadata.

Audit this explicitly.

If we intentionally experiment with LLM-generated rationales as training supervision, design the training process so that the model does not require unavailable future information during inference.

# 10. Core Model: OpenTSLM

The primary model for this project is **OpenTSLM — Open Time-Series Language Models**.

Do **not** substitute OpenLTM, Timer, Timer-XL, or a conventional LSTM unless they are being used strictly as comparison baselines.

OpenTSLM treats time series as a native modality alongside language, allowing a language model to reason directly over temporal signals.

This is especially relevant to Open Relief because our system needs to combine multiple time-series signals and ideally produce both:

* predictions;
* interpretable reasoning/explanations.

Inspect the current official OpenTSLM repository, paper, pretrained checkpoints, and documentation before implementing the model pipeline.

The official project currently includes architectures such as:

* **OpenTSLM-SP** — soft-prompt-based time-series integration;
* **OpenTSLM-Flamingo** — cross-attention-based integration inspired by Flamingo.

Do not assume beforehand which architecture is best for Open Relief.

Investigate both and determine which is most practical for our dataset, compute budget, and hackathon timeline.

OpenTSLM currently supports pretrained language-model backbones such as Llama and Gemma variants and provides pretrained model loading and fine-tuning infrastructure.

Use the existing OpenTSLM implementation rather than reimplementing the architecture from scratch unless absolutely necessary.

# 11. Adapting OpenTSLM to Open Relief

OpenTSLM was originally demonstrated heavily on medical and general time-series reasoning tasks.

Our task is to adapt the architecture to a new domain:

**multivariate geopolitical, climate, trade, logistics, and food-security time series.**

Determine how our data should be represented using OpenTSLM's expected input format.

Investigate:

* how individual time series are encoded;
* how multiple time series are interleaved;
* how textual descriptions of each signal are supplied;
* expected patch sizes;
* variable sequence lengths;
* normalization requirements;
* context-window constraints;
* how the model handles multiple time-series channels;
* how prompts and time-series chunks should be structured.

A conceptual Open Relief sample may contain:

* shipping-volume series;
* import-volume series;
* rainfall series;
* conflict-event series;
* commodity or food-price series;
* food-security history;
* textual metadata describing the country and each signal.

The model might then receive a question such as:

> Based only on the information available up to this date, is food insecurity in this region likely to deteriorate within the next N weeks/months? Explain the temporal signals that support your prediction.

The exact prompt and output schema should be determined experimentally.

# 12. OpenTSLM Training Dataset

Create an OpenTSLM-compatible training dataset from the unified Open Relief dataset.

Each sample should include the appropriate combination of:

* time-series tensors;
* descriptions of those series;
* geographic context;
* prediction cutoff;
* question/instruction;
* structured prediction target;
* optional explanatory target.

If helpful, use the annotation pipeline to produce richer supervised examples resembling:

**Input**

Historical time series from multiple sources.

**Question**

What is likely to happen to food security over the defined forecast horizon?

**Target answer**

A structured outcome plus reasoning.

For example conceptually:

`Risk: HIGH`

`Expected direction: DETERIORATING`

`Confidence: 0.82`

`Reasoning: Maritime imports have declined for several weeks while conflict incidents and rainfall anomalies have increased...`

Do not hard-code this exact format unless it proves suitable for OpenTSLM training.

# 13. Baseline OpenTSLM Evaluation

Before fine-tuning, establish a baseline using the original/pretrained OpenTSLM model.

The baseline should answer:

> How capable is OpenTSLM at this task before being adapted to Open Relief?

Use the closest appropriate pretrained OpenTSLM checkpoint and a reproducible evaluation prompt.

Evaluate it on a held-out subset before Open Relief fine-tuning.

If direct zero-shot evaluation is meaningful, include it.

If minimal task adaptation is required for the model to produce a valid output, document that clearly.

Also consider one simple non-OpenTSLM baseline if it can be implemented cheaply.

The core comparison remains:

**pretrained OpenTSLM → Open Relief fine-tuned OpenTSLM**

# 14. Fine-Tuning OpenTSLM

Fine-tune OpenTSLM on the Open Relief dataset.

Use the official OpenTSLM training infrastructure as much as possible.

Determine whether **OpenTSLM-SP** or **OpenTSLM-Flamingo** is preferable based on:

* GPU/VRAM requirements;
* training speed;
* multimodal capacity;
* number of time series per example;
* quality of temporal reasoning;
* implementation maturity;
* fine-tuning complexity;
* hackathon constraints.

If compute allows, a small preliminary comparison between the two architectures is useful.

Otherwise, select one, document the reasoning, and proceed.

The training pipeline should track:

* base OpenTSLM checkpoint;
* LLM backbone;
* OpenTSLM architecture;
* dataset version;
* feature configuration;
* forecast horizon;
* training range;
* validation range;
* test range;
* hyperparameters;
* random seed;
* experiment metrics.

The primary experiment is:

**Pretrained OpenTSLM → Open Relief fine-tuning → held-out evaluation**

# 15. Evaluation and Leakage Prevention

Evaluation quality is one of the most important parts of the project.

Do not randomly shuffle temporally related observations into train and test sets if doing so would expose future information.

Prefer chronological evaluation.

Conceptually:

`TRAIN → VALIDATION → TEST`

where the test period represents genuinely later observations.

Consider rolling-origin or walk-forward evaluation if feasible.

Also consider geographic generalization if the data permit it:

* future periods in countries represented during training;
* unseen countries or regions;
* crisis episodes not represented during training.

The exact quantitative metrics depend on the final target.

For deterioration-event prediction, useful metrics may include:

* precision;
* recall;
* F1;
* PR-AUC;
* ROC-AUC;
* calibration;
* lead time before deterioration.

For regression or ordinal forecasting, select appropriate alternatives.

Because this is an early-warning system, **lead time** is particularly important.

A model that correctly identifies a crisis several weeks earlier may be substantially more useful than one that only becomes confident when the deterioration is already obvious.

# 16. Evaluate Explanations Separately

OpenTSLM may produce natural-language reasoning in addition to the quantitative prediction.

Evaluate these two capabilities separately.

### Prediction quality

Does the model correctly predict future deterioration?

### Explanation quality

Does the explanation correctly identify relevant patterns in the input data?

Do not allow an impressive-sounding explanation to compensate for an incorrect prediction.

For selected examples, compare the model's reasoning against:

* actual time-series changes;
* LLM annotations;
* known historical events;
* retrieved evidence where available.

# 17. Core Hackathon Demonstration

The final experiment should make the following comparison extremely clear.

### Baseline

Original/pretrained OpenTSLM before Open Relief fine-tuning.

### Open Relief

The same OpenTSLM architecture after domain-specific fine-tuning on our multimodal crisis dataset.

### Result

Measure whether fine-tuning improves the model's ability to predict food-security deterioration on unseen future periods.

Show a concise benchmark table.

For example:

| Model         |  F1 | Recall | PR-AUC | Mean Warning Lead Time |
| ------------- | --: | -----: | -----: | ---------------------: |
| Base OpenTSLM | ... |    ... |    ... |                    ... |
| Open Relief   | ... |    ... |    ... |                    ... |

Use the actual metrics appropriate to the final task rather than blindly using these examples.

Also create one or two strong visual case studies.

For example:

`shipping decline`
↓
`rainfall anomaly`
↓
`conflict escalation`
↓
`import decline`
↓
`Open Relief warning`
↓
`observed food-security deterioration`

Show the model prediction **before** the observed deterioration whenever possible.

# 18. Explainability

A major advantage of using OpenTSLM should be its ability to reason over time-series signals rather than simply outputting a number.

For selected predictions, produce human-readable explanations showing which signals the model considered relevant.

For example:

> Maritime import volumes began declining six weeks before the prediction cutoff. During the same period, conflict incidents rose sharply and rainfall remained below the historical seasonal range. Together, these patterns are consistent with increased food-security risk over the next forecast window.

These explanations may combine:

* direct observations;
* learned temporal patterns;
* LLM historical knowledge;
* retrieved context.

Where appropriate, differentiate between what the data directly shows and what the model is inferring.

Do not require every explanation to be externally cited, but verify particularly important, surprising, or uncertain historical claims when practical.

# 19. Repository Structure

Design the project so another engineer can understand and reproduce it after the hackathon.

A reasonable high-level separation might be:

`open-relief-data/`

* acquisition;
* source connectors;
* normalization;
* standardized outputs.

`open-relief/`

* dataset construction;
* annotation;
* OpenTSLM adapters;
* training;
* evaluation;
* visualization;
* demo.

Do not force this exact structure if the existing repositories suggest something better.

Prefer:

* Python;
* typed interfaces where useful;
* small composable modules;
* configuration files rather than hard-coded parameters;
* deterministic dataset creation;
* environment-variable API keys;
* clear READMEs;
* explicit CLI commands;
* tests for important transformations;
* tests for temporal leakage.

Never commit secrets or API keys.

Include `.env.example` where appropriate.

# 20. Reproducibility

Another team member should be able to reproduce the central experiment.

Document commands similar in spirit to:

`fetch data`

`build dataset`

`generate annotations`

`run baseline`

`fine-tune OpenTSLM`

`evaluate`

`generate demo figures`

The actual CLI design is up to you.

Cache expensive intermediate results where appropriate, especially:

* downloaded external data;
* processed datasets;
* OpenAI annotation responses;
* trained model checkpoints.

# 21. Expected Deliverables

By the end of the implementation, aim to have:

1. a reproducible data-acquisition repository;
2. standardized source connectors;
3. a unified multivariate time-series dataset;
4. an LLM annotation pipeline;
5. structured historical annotations;
6. an OpenTSLM-compatible dataset adapter;
7. baseline OpenTSLM evaluation;
8. OpenTSLM fine-tuning scripts;
9. leakage-aware temporal evaluation;
10. benchmark results comparing pretrained and fine-tuned OpenTSLM;
11. example model explanations;
12. prediction visualizations;
13. documentation describing architecture and reproduction steps;
14. a concise hackathon demo path.

# 22. How You Should Work

Follow this process.

## Phase 1 — Discovery

Inspect:

* `HANDOFF.md`;
* the repository;
* available datasets;
* existing code;
* the official OpenTSLM repository and documentation.

Summarize your understanding of:

* project objective;
* prediction target;
* datasets;
* time ranges;
* geographic units;
* OpenTSLM integration;
* existing implementation;
* missing components.

Then identify genuine ambiguities.

## Phase 2 — Clarification

Ask all important clarifying questions together.

For each question, briefly explain why it affects the implementation.

Skip questions that can be answered from the repository or documentation.

Do not block progress on minor uncertainties.

## Phase 3 — Architecture and Plan

Produce a concrete implementation plan covering:

* system architecture;
* repository boundaries;
* directory structure;
* dataset schema;
* data flow;
* annotation flow;
* OpenTSLM input format;
* OpenTSLM fine-tuning strategy;
* temporal leakage safeguards;
* evaluation strategy;
* implementation milestones;
* expected output from each milestone.

Prioritize tasks as:

* **Must have**
* **Should have**
* **Nice to have**

Keep the solution scoped appropriately for a hackathon.

## Phase 4 — Execution

After presenting the plan, begin implementing it.

Do not stop after producing architectural recommendations.

Execute the plan step by step.

For each step:

1. explain what you are implementing;
2. create or modify the necessary files;
3. run relevant commands or tests;
4. inspect the results;
5. fix failures;
6. update implementation status;
7. continue.

Do not create placeholder implementations when a working version is feasible.

# 23. Decision-Making Rules

When you encounter uncertainty:

* inspect the repository first;
* inspect `HANDOFF.md`;
* inspect the official OpenTSLM implementation;
* consult authoritative documentation when needed;
* use LLM internal knowledge when useful;
* retrieve external information when confidence is low or verification is important;
* clearly state consequential assumptions;
* prefer reproducibility over unnecessary cleverness;
* prefer a working hackathon-scale solution over unnecessary infrastructure;
* prevent accidental temporal leakage;
* do not claim benchmark improvements before measuring them.

If a non-blocking implementation detail is unclear, choose a sensible default, state the assumption, and continue.

If a decision fundamentally changes the project objective, target definition, or evaluation methodology, ask me first.

# 24. External References

Use these authoritative resources where relevant:

### OpenTSLM

Use the **official OpenTSLM website, paper, GitHub repository, Python package, and official pretrained checkpoints** as the primary references for the model.

Important concepts to investigate include:

* Time-Series Language Models;
* OpenTSLM-SP;
* OpenTSLM-Flamingo;
* time-series patch encoding;
* interleaving text and time-series inputs;
* pretrained Llama/Gemma backbones;
* OpenTSLM fine-tuning;
* Hugging Face pretrained checkpoints.

### IMF PortWatch

Use the official IMF PortWatch platform and API/documentation for maritime-trade and port-activity data.

### OpenAI API

Use the current official OpenAI developer documentation when implementing the annotation service, structured outputs, API calls, and model selection.

If an external API, model, or repository has changed since `HANDOFF.md` was written, follow the current authoritative implementation and document any consequential discrepancy.

# 25. Immediate Task

Start now with **Phase 1 — Discovery**.

First:

1. read `HANDOFF.md`;
2. inspect the repository;
3. inspect the official OpenTSLM architecture and available checkpoints;
4. identify the target and datasets;
5. summarize your understanding;
6. ask any genuinely blocking clarification questions;
7. produce the implementation plan;
8. begin executing it.
