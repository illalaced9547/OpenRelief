"""Full-2,230-example evaluation of the ALREADY fine-tuned checkpoint (no retraining).

The in-flight "fulleval" jobs retrain from scratch before evaluating, which takes
hours. This loads the existing gpu-run-2781/best_model.pt LoRA adapter directly and
only runs inference, sharded like pretrained_eval.py, to get the same full-test-set
number in minutes instead of hours.
"""
import argparse
import json
from pathlib import Path
from .adapter import format_input
from .dataset import load_examples
from .evaluate import parse_prediction

REPO_ID = "Alaeddinnn/OpenRelief"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dataset", type=Path)
    p.add_argument("adapter_path", type=Path, help="path to best_model.pt (LoRA adapter)")
    p.add_argument("--checkpoint", default="OpenTSLM/llama-3.2-1b-tsqa-sp")
    p.add_argument("--shard-index", type=int, required=True)
    p.add_argument("--shard-count", type=int, required=True)
    p.add_argument("--output", type=Path, default=Path("/tmp/shard.jsonl"))
    p.add_argument("--hf-path", default=None, help="path_in_repo to upload the shard to; skip upload if omitted")
    a = p.parse_args()
    if not (0 <= a.shard_index < a.shard_count):
        p.error("shard-index must be in [0, shard-count)")
    import torch
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from opentslm.model.llm.OpenTSLMSP import OpenTSLMSP
    from opentslm.time_series_datasets.util import extend_time_series_to_match_patch_size_and_aggregate
    if not torch.cuda.is_available():
        p.error("Run on a machine with CUDA available")
    api = HfApi()
    checkpoint_sha = api.model_info(a.checkpoint).sha
    backbone = "meta-llama/Llama-3.2-1B"
    backbone_sha = api.model_info(backbone).sha
    backbone_path = snapshot_download(backbone, revision=backbone_sha)
    path = hf_hub_download(a.checkpoint, "model_checkpoint.pt", revision=checkpoint_sha)
    model = OpenTSLMSP(llm_id=backbone_path, device="cuda")
    model.load_from_file(path)
    model.enable_lora(lora_r=16, lora_alpha=32, lora_dropout=0.0)
    model.load_from_file(str(a.adapter_path))
    model.eval()
    print(f"Loaded base {a.checkpoint}@{checkpoint_sha[:12]} + LoRA adapter {a.adapter_path}", flush=True)
    patch_size = getattr(model, "patch_size", 4)

    def collate(sample):
        return extend_time_series_to_match_patch_size_and_aggregate([sample], patch_size=patch_size, normalize=False)

    test = sorted(load_examples(a.dataset, "test"), key=lambda e: e["input"]["sample_id"])
    shard = test[a.shard_index::a.shard_count]
    print(f"Shard {a.shard_index}/{a.shard_count}: {len(shard)}/{len(test)} examples", flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with torch.no_grad():
        for i, e in enumerate(shard):
            raw = model.generate(collate(format_input(e["input"])), max_new_tokens=256, do_sample=False)[0]
            parsed = parse_prediction(raw)
            last = e["input"]["last_available_phase"]
            row = {"sample_id": e["input"]["sample_id"], "true_phase": e["target"]["phase"],
                   "predicted_phase": parsed["phase"] if parsed else 0, "raw_output": raw,
                   "country": e["input"]["geography"]["country"], "cutoff": e["input"]["cutoff"],
                   "target_month": e["target"]["target_month"],
                   "baseline_phase": last["phase"] if last else None}
            rows.append(row)
            print(f"{i + 1}/{len(shard)} id={row['sample_id']} true={row['true_phase']} pred={row['predicted_phase']}",
                  flush=True)
    a.output.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"Wrote {len(rows)} rows to {a.output}", flush=True)
    if a.hf_path:
        api.upload_file(path_or_fileobj=str(a.output), path_in_repo=a.hf_path, repo_id=REPO_ID, repo_type="dataset")
        print(f"Uploaded to hf://datasets/{REPO_ID}/{a.hf_path}", flush=True)


if __name__ == "__main__":
    main()
