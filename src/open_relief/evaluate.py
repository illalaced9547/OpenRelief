"""Quantitative IPC scoring independent of explanation quality."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .dataset import load_examples


def parse_prediction(text: str) -> dict | None:
    try:
        value = json.loads(text.strip().removeprefix('```json').removesuffix('```').strip())
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or type(value.get("phase")) is not int or value["phase"] not in range(1, 6):
        return None
    if not isinstance(value.get("rationale"), str):
        return None
    return value


def score(rows: list[dict]) -> dict:
    from sklearn.metrics import accuracy_score, f1_score, recall_score, cohen_kappa_score
    if not rows:
        raise ValueError("Cannot score empty predictions")
    truth = [r["true_phase"] for r in rows]
    pred = [r["predicted_phase"] if r["predicted_phase"] in range(1, 6) else 0 for r in rows]
    valid = [i for i, p in enumerate(pred) if p != 0]
    result = {"n": len(rows), "accuracy": accuracy_score(truth, pred),
        "macro_f1_present_classes": f1_score(truth, pred, labels=sorted(set(truth)), average="macro", zero_division=0),
        "macro_f1_all_five": f1_score(truth, pred, labels=[1,2,3,4,5], average="macro", zero_division=0),
        "phase_recall": dict(zip(map(str, range(1,6)), recall_score(truth,pred,labels=[1,2,3,4,5],average=None,zero_division=0).tolist())),
        "invalid_rate": 1-len(valid)/len(rows),
        "ordinal_mae_valid_only": sum(abs(truth[i]-pred[i]) for i in valid)/len(valid) if valid else None}
    eligible = [r for r in rows if r.get("baseline_phase") is not None]
    if eligible:
        y = [r["true_phase"] > r["baseline_phase"] for r in eligible]
        p = [r["predicted_phase"] > r["baseline_phase"] if r["predicted_phase"] else False for r in eligible]
        result["secondary_deterioration"] = {"n": len(y), "f1": f1_score(y,p,zero_division=0),
            "recall": recall_score(y,p,zero_division=0),
            "definition": "Any phase increase over available assessment; invalid predictions count as no alert."}
    return result


def baseline(dataset: Path, output: Path):
    train, test = load_examples(dataset, "train"), load_examples(dataset, "test")
    majority = Counter(e["target"]["phase"] for e in train).most_common(1)[0][0]
    output.mkdir(parents=True, exist_ok=True)
    (output / "run.json").write_text(json.dumps({"dataset_version": train[0]["input"]["dataset_version"], "evaluation_split": "test"}, indent=2)+"\n")
    metrics = {}
    for name in ("training_majority", "last_available_phase"):
        rows = []
        for e in test:
            last = e["input"]["last_available_phase"]
            phase = last["phase"] if name == "last_available_phase" and last else majority
            rows.append({"sample_id": e["input"]["sample_id"], "country": e["input"]["geography"]["country"],
                "cutoff": e["input"]["cutoff"], "target_month": e["target"]["target_month"],
                "true_phase": e["target"]["phase"], "predicted_phase": phase,
                "baseline_phase": last["phase"] if last else None})
        metrics[name] = score(rows)
        (output / f"{name}.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    (output / "baseline-metrics.json").write_text(json.dumps(metrics, indent=2)+"\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("dataset",type=Path); p.add_argument("--output",type=Path,default=Path("artifacts/evaluation"))
    a=p.parse_args(); baseline(a.dataset,a.output)
