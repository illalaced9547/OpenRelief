import argparse
import json
from pathlib import Path
from .audit import audit_hfid
from .dataset import build_dataset


def main():
    parser = argparse.ArgumentParser(description="Open Relief reproducible discovery")
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("csv", type=Path)
    audit.add_argument("--output", type=Path, required=True)
    audit.add_argument("--window", type=int, default=12)
    audit.add_argument("--horizon", type=int, default=3)
    build = commands.add_parser("build")
    build.add_argument("csv", type=Path)
    build.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    build.add_argument("--output", type=Path, default=Path("artifacts/dataset"))
    args = parser.parse_args()
    if args.command == "build":
        result = build_dataset(args.csv, args.config, args.output)
        print(json.dumps({"dataset_version": result["dataset_version"], "counts": result["counts"]}))
        return
    result = audit_hfid(args.csv, args.window, args.horizon)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"report": str(args.output), "rows": result["rows"],
                      "candidate_windows": result["window_audit"]["samples"]}))


if __name__ == "__main__":
    main()
