"""Cheap train-only classical ablations; not a substitute for OpenTSLM."""
import argparse
import json
from pathlib import Path
import numpy as np
from .dataset import load_examples
from .evaluate import score


def features(sample, drop):
    out=[]
    for c in sample["channels"]:
        if any(c["name"].startswith(x) for x in drop):continue
        indices=np.array([i for i,v in enumerate(c["values"]) if v is not None])
        values=np.array([v for v in c["values"] if v is not None],dtype=float)
        if len(values):
            trend=float(np.polyfit(indices,values,1)[0]) if len(values)>1 else 0.0
            out.extend([float(values[-1]),float(values.mean()),float(values.std()),trend,len(values)/len(c["values"])])
        else:out.extend([float("nan")]*4+[0.0])
    last=sample["last_available_phase"]
    out.extend([last["phase"] if last else float("nan"),float(last is not None)])
    return out


def main():
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    p=argparse.ArgumentParser();p.add_argument("dataset",type=Path);p.add_argument("--output",type=Path,default=Path("artifacts/ablations"))
    p.add_argument("--split", choices=["validation", "test"], default="validation")
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    train=load_examples(a.dataset,"train");test=load_examples(a.dataset,a.split)
    (a.output/"run.json").write_text(json.dumps({"dataset_version": train[0]["input"]["dataset_version"], "evaluation_split": a.split}, indent=2)+"\n")
    y=[e["target"]["phase"] for e in train]
    settings={"all_sources":(),"food_history_only":("portwatch_","acled_","chirps_","wfp_"),
        "without_shipping":("portwatch_",),"without_conflict":("acled_",),
        "without_rainfall":("chirps_",),"without_prices":("wfp_",)}
    metrics={}
    for name,drop in settings.items():
        model=make_pipeline(SimpleImputer(strategy="median",keep_empty_features=True),StandardScaler(),
            LogisticRegression(max_iter=2000,class_weight="balanced",random_state=42))
        model.fit([features(e["input"],drop) for e in train],y)
        predictions=model.predict([features(e["input"],drop) for e in test])
        rows=[]
        for e,pred in zip(test,predictions):
            last=e["input"]["last_available_phase"]
            rows.append({"sample_id":e["input"]["sample_id"],"true_phase":e["target"]["phase"],"predicted_phase":int(pred),
                "country":e["input"]["geography"]["country"],"baseline_phase":last["phase"] if last else None})
        metrics[name]=score(rows)
        (a.output/f"{name}.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    (a.output/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
    lines=["# Classical exploratory ablations", "", f"Evaluation partition: {a.split}.", "Logistic regression; all preprocessing fitted on training only. These are not OpenTSLM results.",
        "No hyperparameter selection used test data. Ablations measure association, not causality.","", "| Features | Macro-F1 (present classes) | Accuracy |", "|---|---:|---:|"]
    for name,m in metrics.items():lines.append(f"| {name} | {m['macro_f1_present_classes']:.4f} | {m['accuracy']:.4f} |")
    (a.output/"benchmark.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":main()
