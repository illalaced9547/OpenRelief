"""Content-addressed downloads with immutable provenance and bounded retries."""
import hashlib
import json
import os
import tempfile
import time
import ssl
import certifi
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(url: str, cache: Path, refresh: bool = False, attempts: int = 3) -> tuple[Path, dict]:
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS sources are supported")
    if attempts < 1:
        raise ValueError("attempts must be positive")
    cache.mkdir(parents=True, exist_ok=True)
    request_id = hashlib.sha256(url.encode()).hexdigest()
    index = cache / f"{request_id}.json"
    if index.exists() and not refresh:
        metadata = json.loads(index.read_text())
        blob = cache / metadata["sha256"]
        if blob.exists():
            with blob.open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != metadata["sha256"]:
                raise ValueError(f"Corrupt cached download: {blob}")
            return blob, metadata
    for attempt in range(attempts):
        temporary = None
        try:
            with urlopen(Request(url, headers={"User-Agent": "OpenRelief/0.1"}), timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as response:
                digest, size = hashlib.sha256(), 0
                with tempfile.NamedTemporaryFile(dir=cache, delete=False) as handle:
                    temporary = Path(handle.name)
                    while chunk := response.read(1024 * 1024):
                        handle.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                expected = response.headers.get("Content-Length")
                if expected and size != int(expected):
                    raise IOError("Incomplete download")
                metadata = {"url": url, "resolved_url": response.url, "sha256": digest.hexdigest(),
                            "bytes": size, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                            "etag": response.headers.get("ETag"),
                            "last_modified": response.headers.get("Last-Modified"),
                            "availability_policy": "retrieval time; not a historical publication timestamp"}
            blob = cache / metadata["sha256"]
            os.replace(temporary, blob)
            payload = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
            # Preserve a manifest for every retrieval, including unchanged content.
            snapshot = cache / f"{request_id}-{time.time_ns()}.manifest.json"
            snapshot.write_text(payload)
            with tempfile.NamedTemporaryFile(mode="w", dir=cache, delete=False) as handle:
                handle.write(payload)
                temporary = Path(handle.name)
            os.replace(temporary, index)
            return blob, metadata
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            retryable = not isinstance(error, HTTPError) or error.code in (408, 429, 500, 502, 503, 504)
            if not retryable or attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    raise RuntimeError("Download attempts exhausted")


def fetch_json(url: str, cache: Path, refresh: bool = False) -> tuple[dict, dict]:
    blob, metadata = fetch(url, cache, refresh)
    value = json.loads(blob.read_text())
    if not isinstance(value, dict) or "error" in value:
        raise ValueError(f"Source returned invalid response: {value}")
    return value, metadata
