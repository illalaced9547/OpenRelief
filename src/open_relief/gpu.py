"""Run the identical held-out cohort before/after adapting official OpenTSLM.

The small explicit loop reuses official architecture, compute_loss, collator,
LoRA and checkpoint methods. Batch size one avoids upstream SP's unmasked padded
answer tokens; gradient accumulation controls effective batch size.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random
from .adapter import format_input, format_training
from .dataset import load_examples, digest_file
from .evaluate import parse_prediction, score

UPSTREAM_COMMIT = "2968f4b891baab4307f7e9d0043e87677b593a30"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("dataset",type=Path)
    p.add_argument("--annotations",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("artifacts/gpu-run"))
    p.add_argument("--checkpoint",default="OpenTSLM/llama-3.2-1b-tsqa-sp")
    p.add_argument("--revision",default="main")
    p.add_argument("--epochs",type=int,default=10)
    p.add_argument("--patience",type=int,default=3)
    p.add_argument("--accumulate",type=int,default=8)
    p.add_argument("--eval-limit",type=int,default=256)
    p.add_argument("--drop-source",action="append",default=[])
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--skip-pretrain-eval",action="store_true")
    a=p.parse_args()
    if min(a.epochs,a.accumulate,a.eval_limit,a.patience)<1:
        p.error("Epochs, accumulation, evaluation limit and patience must be positive")
    import torch
    import numpy as np
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from opentslm.model.llm.OpenTSLMSP import OpenTSLMSP
    from opentslm.model.llm.OpenTSLMFlamingo import OpenTSLMFlamingo
    from opentslm.time_series_datasets.util import extend_time_series_to_match_patch_size_and_aggregate
    if not torch.cuda.is_available():
        p.error("Run on the GPU training machine with CUDA available")
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.cuda.manual_seed_all(a.seed)
    if a.output.exists() and any(a.output.iterdir()):
        p.error("Choose an empty output directory to preserve previous experiments")
    a.output.mkdir(parents=True,exist_ok=True)
    train=load_examples(a.dataset,"train")
    val=sorted(load_examples(a.dataset,"validation"),key=lambda e:e["input"]["sample_id"])[:a.eval_limit]
    test=sorted(load_examples(a.dataset,"test"),key=lambda e:e["input"]["sample_id"])[:a.eval_limit]
    annotations={r["sample_id"]:r for r in map(json.loads,a.annotations.read_text().splitlines())}
    ids = {e["input"]["sample_id"] for e in train}
    if not annotations:
        p.error("Annotations file is empty. Fine-tuning requires at least some annotated examples.")
    if not set(annotations)<=ids:
        p.error("Annotations file contains sample IDs outside the training partition; check dataset/annotation match.")
    annotation_coverage = len(annotations)/len(ids)
    if annotation_coverage < 1.0:
        print(json.dumps({"warning":"partial annotation coverage","annotated":len(annotations),
            "train_total":len(ids),"coverage":round(annotation_coverage,4),
            "effect":"examples without an annotation train on phase only, empty rationale"}),flush=True)
    for e in train:
        annotation=annotations.get(e["input"]["sample_id"])
        if annotation is not None:
            format_training(e, "", annotation)
    print(f"Loaded {len(train)} train / {len(val)} validation / {len(test)} test examples; "
          f"{len(annotations)}/{len(train)} training examples have annotations "
          f"({len(train)-len(annotations)} will train on phase-only supervision, rationale='').",flush=True)
    api=HfApi(); checkpoint_sha=api.model_info(a.checkpoint,revision=a.revision).sha
    if not a.checkpoint.startswith("OpenTSLM/llama-3.2-1b-"):
        p.error("This reproducible runner currently supports official Llama 3.2 1B SP/Flamingo checkpoints")
    backbone="meta-llama/Llama-3.2-1B"
    backbone_sha=api.model_info(backbone).sha
    backbone_path=snapshot_download(backbone,revision=backbone_sha)
    path=hf_hub_download(a.checkpoint,"model_checkpoint.pt",revision=checkpoint_sha)
    if a.checkpoint.endswith("-sp"):
        model=OpenTSLMSP(llm_id=backbone_path,device="cuda")
    elif a.checkpoint.endswith("-flamingo"):
        model=OpenTSLMFlamingo(llm_id=backbone_path,device="cuda",cross_attn_every_n_layers=1,gradient_checkpointing=False)
    else:
        p.error("Unknown architecture")
    model.load_from_file(path)
    print(f"Checkpoint loaded: {a.checkpoint}@{checkpoint_sha[:12]} on backbone {backbone}@{backbone_sha[:12]}.",flush=True)
    eos=model.get_eos_token()
    patch_size=getattr(model,"patch_size",4)
    def collate(sample):
        return extend_time_series_to_match_patch_size_and_aggregate([sample],patch_size=patch_size,normalize=False)
    manifest={"upstream_commit":UPSTREAM_COMMIT,"checkpoint":a.checkpoint,"checkpoint_revision":checkpoint_sha,
        "backbone":backbone,"backbone_revision":backbone_sha,"checkpoint_sha256":digest_file(Path(path)),
        "dataset":json.loads((a.dataset/"manifest.json").read_text()),"seed":a.seed,
        "epochs":a.epochs,"patience":a.patience,"effective_batch_size":a.accumulate,"patch_size":patch_size,
        "drop_sources":a.drop_source,"annotation_sha256":digest_file(a.annotations),
        "skip_pretrain_eval":a.skip_pretrain_eval,
        "annotation_coverage":annotation_coverage,"annotated_train_examples":len(annotations),
        "test_ids":[e["input"]["sample_id"] for e in test],"validation_ids":[e["input"]["sample_id"] for e in val],
        "validation_criterion":"Phase-only JSON prefix loss; rationale generation evaluated separately",
        "torch":torch.__version__,"gpu":torch.cuda.get_device_name(),"normalization":"input-window minmax, masks"}
    (a.output/"run.json").write_text(json.dumps(manifest,indent=2)+"\n")
    def evaluate(name):
        model.eval(); rows=[]
        with torch.no_grad():
            for e in test:
                # No answer or future outcome is passed to model.generate.
                result=model.generate(collate(format_input(e["input"],tuple(a.drop_source))),max_new_tokens=256,do_sample=False)[0]
                parsed=parse_prediction(result)
                last=e["input"]["last_available_phase"]
                rows.append({"sample_id":e["input"]["sample_id"],"true_phase":e["target"]["phase"],
                    "predicted_phase":parsed["phase"] if parsed else 0,"raw_output":result,
                    "country":e["input"]["geography"]["country"],"cutoff":e["input"]["cutoff"],
                    "target_month":e["target"]["target_month"],"baseline_phase":last["phase"] if last else None})
        metrics=score(rows)
        metrics["by_country"]={c:score([r for r in rows if r["country"]==c]) for c in sorted({r["country"] for r in rows})}
        (a.output/f"{name}.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
        (a.output/f"{name}-metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
        return metrics
    before=None
    if a.skip_pretrain_eval:
        print("Skipping pretrained-baseline evaluation (--skip-pretrain-eval).",flush=True)
    else:
        before=evaluate("pretrained")
        print(f"Pretrained baseline: macro_f1={before['macro_f1_present_classes']:.4f} "
              f"accuracy={before['accuracy']:.4f} invalid_rate={before['invalid_rate']:.4f}",flush=True)
    if hasattr(model,"enable_lora"):
        model.enable_lora(lora_r=16,lora_alpha=32,lora_dropout=0.0)
    groups=[]
    trainable=0
    for name,parameter in model.named_parameters():
        if parameter.requires_grad and not getattr(parameter,"exclude_from_optimizer",False):
            groups.append({"params":[parameter],"lr":1e-4 if "projector" in name else 2e-4,"weight_decay":0.01})
            trainable+=parameter.numel()
    print(f"LoRA enabled: {trainable:,} trainable params.",flush=True)
    optimizer=torch.optim.AdamW(groups)
    steps_per_epoch=math.ceil(len(train)/a.accumulate)
    total_steps=steps_per_epoch*a.epochs; warmup=max(1,int(total_steps*0.1))
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda step: min((step+1)/warmup,max(0,(total_steps-step)/max(1,total_steps-warmup))))
    best=float("inf"); stale=0; log=[]
    for epoch in range(a.epochs):
        random.Random(a.seed+epoch).shuffle(train); model.train(); optimizer.zero_grad(); losses=[]
        for i,e in enumerate(train):
            sample=format_training(e,eos,annotations.get(e["input"]["sample_id"]),tuple(a.drop_source))
            loss=model.compute_loss(collate(sample))
            if not torch.isfinite(loss):raise RuntimeError("Non-finite training loss")
            group_size=min(a.accumulate,len(train)-(i//a.accumulate)*a.accumulate)
            (loss/group_size).backward(); losses.append(loss.item())
            print(f"epoch {epoch+1}/{a.epochs} sample {i+1}/{len(train)} "
                  f"id={e['input']['sample_id']} loss={loss.item():.4f}",flush=True)
            if (i+1)%a.accumulate==0 or i+1==len(train):
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.0)
                optimizer.step(); scheduler.step(); optimizer.zero_grad()
                print(f"epoch {epoch+1}/{a.epochs} optimizer step {i//a.accumulate+1}/{steps_per_epoch}",flush=True)
        model.eval()
        with torch.no_grad():
            validation_losses = []
            for e in val:
                item = format_input(e["input"], tuple(a.drop_source))
                item["answer"] = '{"phase": ' + str(e["target"]["phase"]) + ','
                validation_losses.append(model.compute_loss(collate(item)).item())
            validation = sum(validation_losses) / len(validation_losses)
        log.append({"epoch":epoch+1,"train_loss":sum(losses)/len(losses),"validation_loss":validation})
        (a.output/"losses.json").write_text(json.dumps(log,indent=2)+"\n")
        print(f"epoch {epoch+1}/{a.epochs} done: "+json.dumps(log[-1]),flush=True)
        if validation<best:
            best=validation; stale=0; model.store_to_file(str(a.output/"best_model.pt"))
            print(f"epoch {epoch+1}: new best validation_loss={validation:.4f}, checkpoint saved.",flush=True)
        else:
            stale+=1
            print(f"epoch {epoch+1}: no improvement ({stale}/{a.patience}).",flush=True)
        if stale>=a.patience:
            print(f"Early stopping after epoch {epoch+1} (patience {a.patience} exceeded).",flush=True)
            break
    model.load_from_file(str(a.output/"best_model.pt"))
    after=evaluate("fine_tuned")
    print(f"Fine-tuned: macro_f1={after['macro_f1_present_classes']:.4f} "
          f"accuracy={after['accuracy']:.4f} invalid_rate={after['invalid_rate']:.4f}",flush=True)
    lines=["| Model | Macro-F1 (present classes) | Accuracy | Invalid output |", "|---|---:|---:|---:|"]
    rows=[("OpenRelief fine-tuned",after)]
    if before is not None:
        rows.insert(0,("Pretrained OpenTSLM",before))
    for name,m in rows:
        lines.append(f"| {name} | {m['macro_f1_present_classes']:.4f} | {m['accuracy']:.4f} | {m['invalid_rate']:.4f} |")
    (a.output/"benchmark.md").write_text("\n".join(lines)+"\n")
    print("Done. Wrote run.json, losses.json, benchmark.md, fine_tuned.jsonl/-metrics.json to "+str(a.output),flush=True)


if __name__=="__main__":main()
