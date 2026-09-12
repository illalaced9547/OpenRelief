import argparse
import json
from pathlib import Path
from .portwatch import fetch_daily
from .http import fetch


def main():
    parser = argparse.ArgumentParser(description="Open Relief acquisition")
    parser.add_argument("--cache", type=Path, default=Path("data/raw/cache"))
    parser.add_argument("--refresh", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    ports = commands.add_parser("portwatch")
    ports.add_argument("--iso3", required=True)
    ports.add_argument("--start", required=True)
    ports.add_argument("--end", required=True)
    ports.add_argument("--output", required=True, type=Path)
    download = commands.add_parser("download")
    download.add_argument("--url", required=True)
    args = parser.parse_args()
    if args.command == "download":
        path, metadata = fetch(args.url, args.cache, args.refresh)
        print(json.dumps({"path": str(path), "metadata": metadata}))
    else:
        observations, manifests = fetch_daily(args.iso3, args.start, args.end, args.cache, args.refresh)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("".join(json.dumps(o.to_dict(), sort_keys=True) + "\n" for o in observations))
        args.output.with_suffix(".manifest.json").write_text(json.dumps({"schema_version": 1,
            "query": {"iso3": args.iso3, "start": args.start, "end": args.end},
            "observations": len(observations), "sources": manifests}, indent=2) + "\n")
        print(json.dumps({"output": str(args.output), "observations": len(observations)}))


if __name__ == "__main__":
    main()
