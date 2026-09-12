"""Causal monthly features computed from existing input observations only."""
import copy


def add_derived_channels(sample):
    channels = {c["name"]: c for c in sample["channels"]}
    specs = [
        ("wfp_staple_price", "change_1m_pct", 1, "percent_change", "%"),
        ("wfp_staple_price", "change_3m_pct", 3, "percent_change", "%"),
        ("acled_events", "sum_3m", 3, "sum", "events"),
        ("portwatch_import_cargo", "vs_previous_3m_pct", 3, "relative_mean", "%"),
    ]
    for source in ("fcs_rt mean", "rcsi_rt mean"):
        specs.extend((source, f"change_{lag}m", lag, "difference", "normalized index difference")
                     for lag in (1, 3))
    for source, suffix, lag, operation, unit in specs:
        if source not in channels:
            continue
        original = channels[source]
        values, times = [], []
        for i in range(len(original["values"])):
            if operation == "sum":
                indices = list(range(i - lag + 1, i + 1))
            elif operation == "relative_mean":
                indices = list(range(i - lag, i + 1))
            else:
                indices = [i - lag, i]
            value = available = None
            if min(indices) >= 0 and all(original["values"][j] is not None for j in indices):
                observations = [original["values"][j] for j in indices]
                if operation == "sum":
                    value = sum(observations)
                elif operation == "difference":
                    value = observations[-1] - observations[0]
                else:
                    denominator = (sum(observations[:-1]) / lag if operation == "relative_mean"
                                   else observations[0])
                    if denominator > 0:
                        value = 100 * (observations[-1] / denominator - 1)
                if value is not None:
                    available = max(original["availability_times"][j] for j in indices)
            values.append(value)
            times.append(available)
        channel = copy.deepcopy(original)
        channel.update(name=f"{source}_{suffix}", values=values, availability_times=times, unit=unit,
                       derived_from=[source],
                       description=f"{operation}, lag/window {lag} months; trailing input observations only. "
                                   "Insufficient history, missing inputs or nonpositive ratio denominators remain null.")
        sample["channels"].append(channel)
