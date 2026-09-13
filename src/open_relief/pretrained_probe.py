"""Diagnostic: is the untrained checkpoint's 0%-valid-JSON result a real capability
gap, or an artifact of greedy decoding / prompt phrasing? Runs a handful of test
examples through several variants and prints everything for manual inspection.
"""
import argparse
import copy
import json
from pathlib import Path
from .adapter import format_input
from .dataset import load_examples
from .evaluate import parse_prediction


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dataset", type=Path)
    p.add_argument("--checkpoint", default="OpenTSLM/llama-3.2-1b-tsqa-sp")
    p.add_argument("--n", type=int, default=8)
    a = p.parse_args()
    import torch
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from opentslm.model.llm.OpenTSLMSP import OpenTSLMSP
    from opentslm.time_series_datasets.util import extend_time_series_to_match_patch_size_and_aggregate
    if not torch.cuda.is_available():
        p.error("Run on the GPU machine with CUDA available")
    api = HfApi()
    checkpoint_sha = api.model_info(a.checkpoint).sha
    backbone = "meta-llama/Llama-3.2-1B"
    backbone_sha = api.model_info(backbone).sha
    backbone_path = snapshot_download(backbone, revision=backbone_sha)
    path = hf_hub_download(a.checkpoint, "model_checkpoint.pt", revision=checkpoint_sha)
    model = OpenTSLMSP(llm_id=backbone_path, device="cuda")
    model.load_from_file(path)
    model.eval()
    print(f"Loaded {a.checkpoint}@{checkpoint_sha[:12]}", flush=True)
    patch_size = getattr(model, "patch_size", 4)

    def collate(sample):
        return extend_time_series_to_match_patch_size_and_aggregate([sample], patch_size=patch_size, normalize=False)

    test = sorted(load_examples(a.dataset, "test"), key=lambda e: e["input"]["sample_id"])[:a.n]

    FEWSHOT_EXAMPLE = (
        "Example of the required output format for a different case: "
        '{"phase": 2, "rationale": "Prices rose while conflict events increased.", '
        '"recommended_actions": ["Expand market monitoring"]}. '
        "Now answer for the case below in the same exact JSON format.\n"
    )

    def run(label, sample, **gen_kwargs):
        with torch.no_grad():
            raw = model.generate(collate(sample), max_new_tokens=256, **gen_kwargs)[0]
        parsed = parse_prediction(raw)
        print(f"  [{label}] valid={parsed is not None} raw={raw[:180]!r}", flush=True)
        return parsed is not None

    valid_counts = {"greedy": 0, "sampled": 0, "fewshot": 0, "forced_prefix": 0}
    for e in test:
        sid = e["input"]["sample_id"]
        country = e["input"]["geography"]["country"]
        print(f"--- {sid} {country} true_phase={e['target']['phase']} ---", flush=True)

        base = format_input(e["input"])
        if run("greedy", base, do_sample=False):
            valid_counts["greedy"] += 1

        if run("sampled(T=0.8)", base, do_sample=True, temperature=0.8, top_p=0.9):
            valid_counts["sampled"] += 1

        fewshot = copy.deepcopy(base)
        fewshot["pre_prompt"] = FEWSHOT_EXAMPLE + fewshot["pre_prompt"]
        if run("fewshot", fewshot, do_sample=False):
            valid_counts["fewshot"] += 1

        forced = copy.deepcopy(base)
        forced["post_prompt"] = base["post_prompt"] + ' {"phase":'
        with torch.no_grad():
            raw = model.generate(collate(forced), max_new_tokens=256, do_sample=False)[0]
        full = '{"phase":' + raw
        parsed = parse_prediction(full)
        print(f"  [forced_prefix] valid={parsed is not None} raw={full[:180]!r}", flush=True)
        if parsed is not None:
            valid_counts["forced_prefix"] += 1

    print("SUMMARY (out of", len(test), "):", json.dumps(valid_counts), flush=True)


if __name__ == "__main__":
    main()
