"""Recompute handoff claims without pandas or imputation."""
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path


def month_index(value: str) -> int:
    year, month = map(int, value.split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month: {value}")
    return year * 12 + month - 1


def month_string(value: int) -> str:
    year, month = divmod(value, 12)
    return f"{year:04d}-{month + 1:02d}"


def audit_hfid(path: Path, window: int = 12, horizon: int = 3) -> dict:
    if window < 1 or horizon < 0:
        raise ValueError("window must be positive; horizon must be nonnegative")
    panel = defaultdict(dict)
    nonnull = Counter()
    phases = {name: Counter() for name in ("ipc_phase_fews", "ipc_phase_ipcch")}
    count = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        required = {"year_month", "ADMIN0", "ADMIN1", "ADMIN2", "ipc_phase_fews",
                    "ipc_phase_ipcch", "fcs_rt mean", "rcsi_rt mean"}
        if not required <= set(columns or []):
            raise ValueError(f"Missing columns: {required - set(columns or [])}")
        for row in reader:
            unit = tuple(row[k] for k in ("ADMIN0", "ADMIN1", "ADMIN2"))
            month = month_index(row["year_month"])
            if month in panel[unit]:
                raise ValueError(f"Duplicate district-month: {unit}, {row['year_month']}")
            panel[unit][month] = row
            count += 1
            nonnull.update(k for k, v in row.items() if v != "")
            for name, counts in phases.items():
                counts[row[name] or "missing"] += 1
    if not count:
        raise ValueError("Empty dataset")
    samples, by_country, by_year, labels, gaps = 0, Counter(), Counter(), Counter(), Counter()
    for unit, months in panel.items():
        ipc_months = sorted(t for t, row in months.items() if row["ipc_phase_fews"])
        gaps.update(b - a for a, b in zip(ipc_months, ipc_months[1:]))
        for cutoff in sorted(months):
            future = months.get(cutoff + horizon, {})
            label = future.get("ipc_phase_fews", "")
            if not label or float(label) not in (1, 2, 3, 4, 5):
                continue
            if all(all(months.get(t, {}).get(k, "") != "" for k in ("fcs_rt mean", "rcsi_rt mean"))
                   for t in range(cutoff - window + 1, cutoff + 1)):
                samples += 1
                by_country[unit[0]] += 1
                by_year[month_string(cutoff)[:4]] += 1
                labels[str(int(float(label)))] += 1
    all_months = [t for months in panel.values() for t in months]
    return {
        "source_file": path.name, "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
        "rows": count, "columns": columns, "countries": len({u[0] for u in panel}),
        "administrative_units": len(panel), "duplicate_district_months": 0,
        "date_range": [month_string(min(all_months)), month_string(max(all_months))],
        "nonnull_counts": dict(nonnull), "phase_counts": {k: dict(v) for k, v in phases.items()},
        "fews_publication_gap_months": dict(sorted(gaps.items())),
        "window_audit": {"window_months": window, "horizon_months": horizon, "samples": samples,
                         "by_country": dict(by_country.most_common()), "by_cutoff_year": dict(sorted(by_year.items())),
                         "labels": dict(sorted(labels.items())),
                         "purpose": "Handoff replication only; no release-lag assumptions or training split applied."},
        "limitations": ["Release timestamps and historical data vintages are absent.",
                        "Before April 2011 FEWS classifications are not the same IPC scale.",
                        "IPCCH phase 6 is unresolved and must not be mapped to IPC phase 5.",
                        "FCS/rCSI normalization and dataset redistribution license need provenance."]}
