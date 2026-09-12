"""Deterministic monthly examples with explicit release-lag assumptions."""
import calendar
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from .audit import month_index, month_string


def digest_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def month_end(t: int) -> str:
    year, month = divmod(t, 12)
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1]).isoformat() + "T23:59:59Z"


def validate_config(config: dict):
    if config["target"] != "ipc_phase_fews":
        raise ValueError("Only agreed FEWS IPC target is supported")
    if config["availability_policy"] != "retrospective_assumed_lag":
        raise ValueError("HFID has no publication timestamps; explicitly opt into assumed lag")
    if config["window_months"] < 1 or config["horizon_months"] < 1 or config["hfid_release_lag_months"] < 0:
        raise ValueError("Invalid window, horizon or release lag")
    ends = [month_index(config[k]) for k in ("train_end", "validation_start", "validation_end", "test_start", "test_end")]
    if not ends[0] < ends[1] <= ends[2] < ends[3] <= ends[4]:
        raise ValueError("Temporal partitions overlap or are out of order")
    if config["features"] != ["fcs_rt mean", "rcsi_rt mean"]:
        raise ValueError("Core feature order must be FCS then rCSI; extra sources use the observations adapter")


def assign_split(cutoff: int, target: int, config: dict) -> str | None:
    label_available = target + config["hfid_release_lag_months"]
    if cutoff <= month_index(config["train_end"]) and label_available <= month_index(config["train_end"]):
        return "train"
    if month_index(config["validation_start"]) <= cutoff <= month_index(config["validation_end"]) and label_available <= month_index(config["validation_end"]):
        return "validation"
    if month_index(config["test_start"]) <= cutoff <= month_index(config["test_end"]):
        return "test"
    return None


def build_dataset(source: Path, config_path: Path, output: Path) -> dict:
    config = json.loads(config_path.read_text())
    validate_config(config)
    source_hash = digest_file(source)
    panel = defaultdict(dict)
    excluded = Counter()
    with source.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if not row["ADMIN2"]:
                excluded["missing_admin2_rows"] += 1
                continue
            key = tuple(row[k] for k in ("iso3", "ADMIN0", "ADMIN1", "ADMIN2"))
            t = month_index(row["year_month"])
            if t in panel[key]:
                raise ValueError(f"Duplicate unit-month: {key}, {t}")
            panel[key][t] = row
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    version = hashlib.sha256((source_hash + config_hash + "dataset-v2-ipc-history").encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    inputs, targets = [], []
    counts, label_counts = Counter(), defaultdict(Counter)
    lag, window, horizon = (config[k] for k in ("hfid_release_lag_months", "window_months", "horizon_months"))
    for unit, history in sorted(panel.items()):
        for target_month, target_row in sorted(history.items()):
            phase = target_row[config["target"]]
            if not phase or target_month < month_index("2011-04"):
                continue
            phase = float(phase)
            if phase not in (1, 2, 3, 4, 5):
                raise ValueError("Invalid FEWS IPC phase")
            cutoff = target_month - horizon
            split = assign_split(cutoff, target_month, config)
            if split is None:
                excluded["purged_or_outside_split"] += 1
                continue
            end = cutoff - lag
            months = list(range(end - window + 1, end + 1))
            if not all(all(history.get(t, {}).get(f, "") != "" for f in config["features"]) for t in months):
                excluded["incomplete_core_window"] += 1
                continue
            channels = []
            for feature in config["features"]:
                values = [float(history[t][feature]) for t in months]
                if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
                    raise ValueError("Expected finite HFID FCS/rCSI values in [0,1]")
                channels.append({"name": feature, "unit": "HFID normalized index (method unknown)",
                    "geography_level": "admin2", "months": [month_string(t) for t in months],
                    "values": values, "availability_times": [month_end(t + lag) for t in months],
                    "availability_basis": "assumed_lag", "source_sha256": source_hash})
            if config.get("calendar_encoding") == "month_of_year":
                channels.append({"name": "month_of_year", "unit": "calendar month (1-12)", "geography_level": "global",
                    "months": [month_string(t) for t in months], "values": [t % 12 + 1 for t in months],
                    "availability_times": [month_end(t) for t in months],
                    "availability_basis": "calendar_known_in_advance", "source_sha256": config_hash})
            phase_history, assessment_age = [], []
            for t in months:
                known = [(d, float(r[config["target"]])) for d, r in history.items()
                         if r[config["target"]] and month_index("2011-04") <= d <= t - lag
                         and t - d <= config["baseline_phase_max_age_months"]]
                latest = max(known) if known else None
                phase_history.append(int(latest[1]) if latest else None)
                assessment_age.append(t - latest[0] if latest else None)
            for name, values, ipc_unit in (("ipc_last_known_phase", phase_history, "IPC phase 1-5"),
                                       ("ipc_assessment_age", assessment_age, "months")):
                channels.append({"name": name, "unit": ipc_unit, "geography_level": "admin2",
                    "description": "Latest assessment available as of each historical month; expires after six months.",
                    "months": [month_string(t) for t in months], "values": values,
                    "availability_times": [month_end(t) for t in months],
                    "availability_basis": "assumed_lag", "source_sha256": source_hash})
            baseline = [(t, float(r[config["target"]])) for t, r in history.items()
                        if r[config["target"]] and month_index("2011-04") <= t <= cutoff - lag
                        and cutoff - t <= config["baseline_phase_max_age_months"]]
            last = max(baseline) if baseline else None
            identity = json.dumps([version, unit, month_string(cutoff)], ensure_ascii=False)
            sample_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
            inputs.append({"sample_id": sample_id, "dataset_version": version, "split": split,
                "geography": dict(zip(("iso3", "country", "admin1", "admin2"), unit)),
                "cutoff": month_end(cutoff), "horizon_months": horizon,
                "channels": channels,
                "last_available_phase": {"phase": int(last[1]), "event_month": month_string(last[0]),
                    "availability_time": month_end(last[0] + lag)} if last else None})
            targets.append({"sample_id": sample_id, "split": split, "phase": int(phase),
                "target_month": month_string(target_month), "label_availability_time": month_end(target_month + lag),
                "phase_change": int(phase - last[1]) if last else None,
                "deteriorated": phase > last[1] if last else None})
            counts[split] += 1
            label_counts[split][str(int(phase))] += 1
    if any(counts[s] == 0 for s in ("train", "validation", "test")):
        raise ValueError(f"Empty partition: {counts}")
    for name, rows in (("inputs.jsonl", inputs), ("targets.jsonl", targets)):
        (output / name).write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows))
    manifest = {"schema_version": 1, "dataset_version": version, "source_sha256": source_hash,
        "config": config, "counts": dict(counts), "labels": {s: dict(c) for s, c in label_counts.items()},
        "excluded": dict(excluded), "files": {n: digest_file(output / n) for n in ("inputs.jsonl", "targets.jsonl")},
        "limitations": ["Retrospective assumed release lags; historical revisions unavailable.",
                         "Core dataset contains FCS/rCSI only until extra source observations are joined.",
                         "Deterioration means at least one phase increase versus a <=6-month-old available assessment."]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def load_examples(directory: Path, split: str) -> list[dict]:
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if digest_file(directory / name) != expected:
            raise ValueError(f"Dataset integrity failure: {name}")
    labels = {r["sample_id"]: r for r in map(json.loads, (directory / "targets.jsonl").read_text().splitlines())}
    result = []
    for row in map(json.loads, (directory / "inputs.jsonl").read_text().splitlines()):
        if row["split"] == split:
            target = labels[row["sample_id"]]
            if target["split"] != split:
                raise ValueError("Input/target partition mismatch")
            result.append({"input": row, "target": target})
    return result
