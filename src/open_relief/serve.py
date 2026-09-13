"""Live inference endpoint for the fine-tuned checkpoint, for the demo frontend.

Reuses the exact input formatting and generation path from gpu.py's own
held-out evaluation loop (format_input + model.generate + parse_prediction),
so served answers are the same shape as the reported benchmark numbers.
Serves stored test-partition examples only: this is a real-time forward pass
through the trained model, not an arbitrary free-form date/country query,
because model input requires the prepared multivariate time-series window.
"""
import os
from pathlib import Path
from .adapter import format_input
from .evaluate import parse_prediction
from .dataset import load_examples

DATASET = Path(os.environ.get("DATASET_DIR", "/workspace/data/multimodal-annotated2781"))
CHECKPOINT_PATH = Path(os.environ.get("CHECKPOINT_PATH", "/workspace/data/gpu-run-2781/best_model.pt"))
BASE_CHECKPOINT = os.environ.get("BASE_CHECKPOINT", "OpenTSLM/llama-3.2-1b-tsqa-sp")

_state: dict = {}


def load_model():
    import torch
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from opentslm.model.llm.OpenTSLMSP import OpenTSLMSP
    from opentslm.time_series_datasets.util import extend_time_series_to_match_patch_size_and_aggregate
    if not torch.cuda.is_available():
        raise RuntimeError("Serving requires CUDA")
    api = HfApi()
    backbone = "meta-llama/Llama-3.2-1B"
    backbone_sha = api.model_info(backbone).sha
    backbone_path = snapshot_download(backbone, revision=backbone_sha)
    model = OpenTSLMSP(llm_id=backbone_path, device="cuda")
    checkpoint_sha = api.model_info(BASE_CHECKPOINT).sha
    base_path = hf_hub_download(BASE_CHECKPOINT, "model_checkpoint.pt", revision=checkpoint_sha)
    model.load_from_file(base_path)
    model.enable_lora(lora_r=16, lora_alpha=32, lora_dropout=0.0)
    model.load_from_file(str(CHECKPOINT_PATH))
    model.eval()
    patch_size = getattr(model, "patch_size", 4)

    def collate(sample):
        return extend_time_series_to_match_patch_size_and_aggregate([sample], patch_size=patch_size, normalize=False)

    test = sorted(load_examples(DATASET, "test"), key=lambda e: e["input"]["sample_id"])
    by_iso3: dict[str, list] = {}
    for e in test:
        by_iso3.setdefault(e["input"]["geography"]["iso3"], []).append(e)
    _state.update(model=model, collate=collate, by_iso3=by_iso3)
    print(f"Loaded checkpoint {CHECKPOINT_PATH}; {len(test)} test examples across "
          f"{len(by_iso3)} countries (iso3): {sorted(by_iso3)}.", flush=True)


def create_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Open Relief inference")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.on_event("startup")
    def _startup():
        load_model()

    @app.get("/healthz")
    def healthz():
        return {"ok": "model" in _state}

    @app.get("/countries")
    def countries():
        return {iso3: len(v) for iso3, v in sorted(_state["by_iso3"].items())}

    @app.get("/predict")
    def predict(iso3: str, index: int = 0):
        import torch
        examples = _state["by_iso3"].get(iso3.upper())
        if not examples:
            raise HTTPException(404, f"No test examples for iso3={iso3!r}. See /countries.")
        if index >= len(examples):
            raise HTTPException(404, f"Only {len(examples)} example(s) available for iso3={iso3!r}.")
        e = examples[index]
        model = _state["model"]
        with torch.no_grad():
            # No answer or future outcome is passed to model.generate.
            raw = model.generate(_state["collate"](format_input(e["input"])), max_new_tokens=256, do_sample=False)[0]
        parsed = parse_prediction(raw)
        last = e["input"]["last_available_phase"]
        return {
            "sample_id": e["input"]["sample_id"], "country": e["input"]["geography"]["country"],
            "iso3": iso3.upper(), "index": index,
            "num_examples_for_country": len(examples),
            "cutoff": e["input"]["cutoff"], "target_month": e["target"]["target_month"],
            "predicted_phase": parsed["phase"] if parsed else None,
            "rationale": parsed["rationale"] if parsed else None,
            "recommended_actions": parsed.get("recommended_actions", []) if parsed else [],
            "raw_output": raw, "valid_output": parsed is not None,
            "true_phase": e["target"]["phase"],
            "baseline_phase": last["phase"] if last else None,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
