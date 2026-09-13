"""OpenTSLM's native dict contract; future labels are absent at inference."""
import json
import math
import statistics


def format_input(sample: dict, drop_sources: tuple[str, ...] = ()) -> dict:
    geography = sample["geography"]
    series, descriptions = [], []
    for channel in sample["channels"]:
        if any(channel["name"].startswith(prefix) for prefix in drop_sources):
            continue
        values = channel["values"]
        observed = [float(v) for v in values if v is not None]
        if any(not math.isfinite(v) for v in observed):
            raise ValueError("Non-finite model input")
        if len(values) != len(channel["months"]):
            raise ValueError("Channel/month length mismatch")
        for v, available in zip(values, channel["availability_times"]):
            if v is not None and (available is None or available > sample["cutoff"]):
                raise ValueError("Future or unknown availability leaked into model input")
        lo, hi = (min(observed), max(observed)) if observed else (0.0, 0.0)
        normalized = [0.0 if v is None or hi == lo else 2*(v-lo)/(hi-lo)-1 for v in values]
        if channel["name"] == "month_of_year":
            normalized = [2 * (float(v) - 1) / 11 - 1 for v in values]  # fixed 1-12 scale, not window fitted
        mask = [float(v is not None) for v in values]
        mean = statistics.mean(observed) if observed else None
        std = statistics.pstdev(observed) if observed else None
        text = (f"{channel['name']}; {channel.get('description', '')}; {channel['unit']}; "
                f"{channel['geography_level']} measurement; monthly {channel['months'][0]} to {channel['months'][-1]}; "
                f"observed mean={mean}, std={std}, min={lo}, max={hi}; "
                "input-window min-max scaled to [-1,1]. Missing entries encoded 0 with separate mask.")
        if channel["name"] == "month_of_year":
            text = "month_of_year: one monthly series, January=1 through December=12; fixed model-input scaling 2*(month-1)/11-1."
        series.extend([normalized, mask])
        descriptions.extend([text, f"Observed mask for {channel['name']}: 1=available observation; 0=missing."])
    prompt = (f"Forecast FEWS NET IPC phase {sample['horizon_months']} months after cutoff {sample['cutoff']}. "
              f"District: {geography['admin2']}, {geography['admin1']}, {geography['country']} ({geography['iso3']}). "
              "Only use available input evidence. IPC phases: 1 Minimal, 2 Stressed, 3 Crisis, 4 Emergency, 5 Famine. "
              "National channels are shared context, not district measurements. "
              "FCS/rCSI are normalized by an undocumented method; do not assume raw thresholds. "
              "Return JSON with integer phase, a concise rationale string, and recommended_actions: a list of "
              "concrete response recommendations grounded only in the given evidence, most urgent first. "
              "Do not invent absent signals. "
              f"Last available IPC assessment: {json.dumps(sample['last_available_phase'])}.")
    return {"pre_prompt": prompt, "post_prompt": "Prediction JSON:", "time_series": series,
            "time_series_text": descriptions}


def format_training(example: dict, eos: str, annotation: dict | None = None, drop_sources=()) -> dict:
    sample = format_input(example["input"], drop_sources)
    answer = {"phase": example["target"]["phase"], "rationale": "", "recommended_actions": []}
    if annotation is not None:
        if annotation["sample_id"] != example["input"]["sample_id"] or annotation["dataset_version"] != example["input"]["dataset_version"]:
            raise ValueError("Annotation belongs to a different sample/dataset")
        if annotation["annotation"]["observed_future_phase"] != answer["phase"]:
            raise ValueError("Annotation label mismatch")
        answer["rationale"] = annotation["annotation"]["rationale"]
        answer["recommended_actions"] = [a["action"] for a in annotation["annotation"]["recommended_actions"]]
    sample["answer"] = json.dumps(answer) + eos
    return sample
