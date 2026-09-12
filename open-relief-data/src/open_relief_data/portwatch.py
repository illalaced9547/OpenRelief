"""Resolve the official IMF item; retrieve bounded daily port data."""
from datetime import date
import re
from pathlib import Path
from urllib.parse import urlencode
from .http import fetch_json
from .schema import Observation

ITEM_ID = "83b1bbc7b3354c5fb1f40673bb8f852e"
ITEM_URL = f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}?f=json"
FEATURES = {"import_dry_bulk": "metric_tons", "import_cargo": "metric_tons",
            "export_cargo": "metric_tons", "portcalls_cargo": "calls"}


def query_url(layer: str, iso3: str, start: str, end: str, offset: int, page_size: int) -> str:
    if not re.fullmatch(r"[A-Z]{3}", iso3):
        raise ValueError("ISO3 must be three uppercase letters")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or offset < 0 or page_size < 1:
        raise ValueError("Invalid date interval or pagination")
    # Integer calendar fields avoid DateOnly/epoch dialect differences in ArcGIS.
    first_key = first.year * 10000 + first.month * 100 + first.day
    last_key = last.year * 10000 + last.month * 100 + last.day
    where = f"ISO3 = '{iso3}' AND (year*10000+month*100+day) >= {first_key} AND (year*10000+month*100+day) <= {last_key}"
    fields = ["ObjectId", "year", "month", "day", "portid", "ISO3", *FEATURES]
    return layer + "/query?" + urlencode({"f": "json", "where": where,
        "outFields": ",".join(fields), "returnGeometry": "false", "orderByFields": "ObjectId ASC",
        "resultOffset": offset, "resultRecordCount": page_size})


def fetch_daily(iso3: str, start: str, end: str, cache: Path, refresh: bool = False):
    query_url("https://validation", iso3, start, end, 0, 1)
    item, item_meta = fetch_json(ITEM_URL, cache, refresh)
    layer = item["url"].rstrip("/") + "/0"
    info, layer_meta = fetch_json(layer + "?f=json", cache, refresh)
    required = {"ObjectId", "year", "month", "day", "portid", "ISO3", *FEATURES}
    if not required <= {f["name"] for f in info["fields"]}:
        raise ValueError("PortWatch schema changed")
    if not info.get("advancedQueryCapabilities", {}).get("supportsPagination"):
        raise ValueError("PortWatch no longer supports pagination")
    size = min(info["maxRecordCount"], 1000)
    offset, seen = 0, set()
    observations, manifests = [], [item_meta, layer_meta]
    while True:
        payload, metadata = fetch_json(query_url(layer, iso3, start, end, offset, size), cache, refresh)
        manifests.append(metadata)
        rows = payload["features"]
        for feature in rows:
            row = feature["attributes"]
            event = date(row["year"], row["month"], row["day"]).isoformat()
            key = (row["portid"], event)
            if key in seen:
                raise ValueError("Duplicate port/day: source may have changed during pagination")
            if row["ISO3"] != iso3 or not start <= event <= end:
                raise ValueError("PortWatch returned records outside requested bounds")
            seen.add(key)
            for name, unit in FEATURES.items():
                observations.append(Observation("imf_portwatch", metadata["sha256"],
                    f"{iso3}:{row['portid']}", "port", name, event, metadata["retrieved_at"],
                    "retrieved", row[name], unit))
        if not payload.get("exceededTransferLimit", False) and len(rows) < size:
            break
        if not rows:
            raise ValueError("Pagination made no progress")
        offset += len(rows)
    return observations, manifests
