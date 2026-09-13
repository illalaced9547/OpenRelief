"""Batch-generate a static prediction snapshot from the live Nebius endpoint.

Run this against src/open_relief/serve.py's URL to refresh
frontend/src/data/live-predictions.json. Intended cadence: daily/weekly against a
live cutoff, not per page view - the frontend reads the committed JSON file
directly and makes no network calls of its own.
"""
import argparse
import datetime
import json
import urllib.request
from pathlib import Path

CHECKPOINT = "gpu-run-2781 (all-sources, epoch 5)"
CHECKPOINT_SHA256 = "a10343caa152d1c3aa55b6dc9b40e11603067babeac44909001d1597a3e84e10"
DATASET_VERSION = "8142c89de89cb862117d6a814be515b9f00312bb960e33cf7e994a99ed124bd3"
OUTPUT = Path(__file__).resolve().parents[1] / "frontend/src/data/live-predictions.json"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("endpoint_url", help="e.g. https://port8080-....tunnel.applications.uk-south2.nebius.cloud")
    p.add_argument("--timeout", type=int, default=60)
    a = p.parse_args()
    base = a.endpoint_url.rstrip("/")
    countries = json.loads(urllib.request.urlopen(f"{base}/countries", timeout=15).read())
    predictions = {}
    for iso3 in countries:
        data = json.loads(urllib.request.urlopen(f"{base}/predict?iso3={iso3}", timeout=a.timeout).read())
        print(f"{iso3}: phase={data['predicted_phase']} valid={data['valid_output']}")
        predictions[iso3] = data
    out = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checkpoint": CHECKPOINT,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "dataset_version": DATASET_VERSION,
        "note": "Batch-generated snapshot; refresh by re-running this script against the live endpoint.",
        "predictions": predictions,
    }
    OUTPUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUTPUT} ({len(predictions)} countries)")


if __name__ == "__main__":
    main()
