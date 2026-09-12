"""Export dated input case studies, attaching actual predictions only when supplied."""
import argparse
import json
from pathlib import Path
from .dataset import load_examples


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from datetime import datetime
    p=argparse.ArgumentParser();p.add_argument("dataset",type=Path)
    p.add_argument("--predictions",type=Path);p.add_argument("--output",type=Path,default=Path("artifacts/demo"))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    examples=load_examples(a.dataset,"test")
    predictions={r["sample_id"]:r for r in map(json.loads,a.predictions.read_text().splitlines())} if a.predictions else {}
    eligible=[e for e in examples if e["target"]["deteriorated"] and (not predictions or e["input"]["sample_id"] in predictions)]
    # Fixed selection rule: two different countries, earliest eligible cutoff, no correctness filtering.
    eligible.sort(key=lambda e:(e["input"]["cutoff"],e["input"]["sample_id"]))
    selected=[];countries=set()
    for e in eligible:
        country=e["input"]["geography"]["country"]
        if country not in countries:selected.append(e);countries.add(country)
        if len(selected)==2:break
    report=[]
    for e in selected:
        sample=e["input"];sid=sample["sample_id"];geo=sample["geography"]
        names=["fcs_rt mean","rcsi_rt mean","portwatch_import_dry_bulk","acled_events","chirps_rainfall","wfp_staple_price"]
        channels=[c for c in sample["channels"] if c["name"] in names]
        fig,axes=plt.subplots(len(channels),1,figsize=(11,2.1*len(channels)),sharex=True,squeeze=False)
        cutoff=datetime.fromisoformat(sample["cutoff"].replace("Z","+00:00")).replace(tzinfo=None)
        target=datetime.fromisoformat(e["target"]["target_month"]+"-01")
        for ax,c in zip(axes[:,0],channels):
            dates=[datetime.fromisoformat(m+"-01") for m in c["months"]]
            values=[v if v is not None else float("nan") for v in c["values"]]
            ax.plot(dates,values,marker="o",linewidth=1.5)
            ax.axvline(cutoff,color="orange",linestyle="--",label="Prediction cutoff")
            ax.axvline(target,color="red",linestyle=":",label="Observed future IPC")
            ax.set_ylabel(c["unit"],fontsize=8);ax.set_title(c["name"]+" ("+c["geography_level"]+")",loc="left",fontsize=10)
            ax.grid(alpha=.2)
        prediction=predictions.get(sid)
        status=f"Model forecast phase {prediction['predicted_phase']}" if prediction else "Input case study — model forecast pending GPU run"
        fig.suptitle(f"{geo['admin2']}, {geo['country']}\n{status}; observed future phase {e['target']['phase']}",fontsize=12)
        axes[0,0].legend(loc="upper left",fontsize=8);fig.tight_layout(rect=(0,0,1,.95))
        fig.savefig(a.output/f"{sid}.png",dpi=150);plt.close(fig)
        report.append({"sample_id":sid,"geography":geo,"cutoff":sample["cutoff"],"target":e["target"],"prediction":prediction})
    (a.output/"cases.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.output/"README.md").write_text("# Case studies\n\nThese are selected by future worsening and earliest cutoff, not prediction correctness.\nOrange marks the cutoff; red marks the observed future assessment. Missing inputs are gaps.\nNational covariates do not imply local exposure or causal attribution.\nModel warnings appear only when actual prediction files are supplied.\n")
    print(json.dumps({"cases":len(report),"output":str(a.output)}))


if __name__=="__main__":main()
