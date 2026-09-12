"""Join national covariates to district histories, respecting assumed release times."""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
from .audit import month_index
from .dataset import digest_file, month_end
from .derived import add_derived_channels

EXTERNAL = ["portwatch_import_dry_bulk", "portwatch_import_cargo", "portwatch_export_cargo",
            "portwatch_portcalls_cargo", "acled_events", "acled_fatalities", "chirps_rainfall", "wfp_staple_price"]


def is_staple_feature(feature):
    if not feature.startswith("wfp_price:"):
        return False
    commodity = feature.split(":", 2)[1].lower().split()
    return bool(commodity) and commodity[0] in {"rice", "wheat", "maize", "sorghum", "millet", "cassava"}


def enrich(dataset: Path, monthly: list[Path], output: Path):
    manifest = json.loads((dataset / "manifest.json").read_text())
    records = []
    for path in monthly:
        records.extend(map(json.loads, path.read_text().splitlines()))
    # Commodity selection uses only months available by the training freeze.
    prices = defaultdict(Counter)
    train_end = month_index(manifest["config"]["train_end"])
    for r in records:
        if is_staple_feature(r["feature"]):
            if month_index(r["month"]) + r["release_lag_months"] <= train_end and r["value"] is not None:
                prices[r["iso3"]][r["feature"]] += 1
    selected = {iso: sorted(counts, key=lambda f: (-counts[f], f))[0] for iso, counts in prices.items()}
    index = {}
    for r in records:
        feature = r["feature"]
        if feature.startswith("wfp_price:"):
            if feature != selected.get(r["iso3"]):
                continue
            feature = "wfp_staple_price"
        key = (r["iso3"], r["month"], feature)
        if key in index:
            raise ValueError(f"Duplicate covariate month: {key}")
        index[key] = r
    source_hashes = {str(p): digest_file(p) for p in monthly}
    version = hashlib.sha256(json.dumps([manifest["dataset_version"], sorted(source_hashes.values()), selected, "enrich-v2-derived"], sort_keys=True).encode()).hexdigest()
    coverage, total = Counter(), Counter()
    rows = []
    for original in map(json.loads, (dataset / "inputs.jsonl").read_text().splitlines()):
        sample = copy.deepcopy(original)
        iso = sample["geography"]["iso3"]
        cutoff = month_index(sample["cutoff"][:7])
        months = sample["channels"][0]["months"]
        sample["dataset_version"] = version
        for feature in EXTERNAL:
            values, times, hashes, unit = [], [], set(), "unknown"
            for m in months:
                r = index.get((iso, m, feature))
                available = month_end(month_index(m) + r["release_lag_months"]) if r else None
                value = r["value"] if r and month_index(m) + r["release_lag_months"] <= cutoff else None
                values.append(value); times.append(available)
                if r:
                    hashes.update(r["source_sha256"]); unit = r["unit"]
                coverage[feature] += int(value is not None); total[feature] += 1
            sample["channels"].append({"name": feature, "unit": unit, "geography_level": "country",
                "description": selected.get(iso, "No training-period staple prices") if feature == "wfp_staple_price" else feature,
                "months": months, "values": values, "availability_times": times,
                "availability_basis": "assumed_lag", "source_sha256": sorted(hashes)})
        add_derived_channels(sample)
        rows.append(sample)
    output.mkdir(parents=True, exist_ok=True)
    (output / "inputs.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    (output / "targets.jsonl").write_bytes((dataset / "targets.jsonl").read_bytes())
    manifest.update({"dataset_version": version, "parent_version": manifest["dataset_version"],
        "derived_features": "Trailing price and food-index changes, conflict sum, import relative change; no extra downloads.",
        "external_monthly_sources": source_hashes, "staple_selection_train_only": selected,
        "external_coverage": {f: {"observed": coverage[f], "total": total[f], "fraction": coverage[f]/total[f]} for f in EXTERNAL},
        "files": {n: digest_file(output/n) for n in ("inputs.jsonl", "targets.jsonl")}})
    manifest["limitations"] = ["Retrospective release-lag assumptions; historical revisions unavailable.",
        "National covariates shared by districts, not local measurements.",
        "Missing ports in landlocked countries are unknown, not zero.",
        "Price medians can change with market composition; exact commodity/unit selected using training only.",
        "Rainfall is country area-weighted monthly average, not a district or crop-season anomaly."]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"counts": manifest["counts"], "coverage": manifest["external_coverage"]}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("dataset", type=Path); p.add_argument("monthly", nargs="+", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); enrich(a.dataset, a.monthly, a.output)
