"""Monthly country-level maritime, conflict, price and CHIRPS features.

Country aggregation is explicit: these are shared national signals, not district
measurements. Every output row carries source hashes and an assumed release lag.
"""
import argparse
import calendar
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics
from urllib.parse import urlencode
from .http import fetch, fetch_json

PORTS_URL = "https://portwatch.imf.org/api/download/v1/items/83b1bbc7b3354c5fb1f40673bb8f852e/csv?layers=0"
COUNTRIES = {"YEM": "yemen", "NGA": "nigeria", "KEN": "kenya", "GTM": "guatemala",
    "MWI": "malawi", "COD": "democratic-republic-of-the-congo", "ZWE": "zimbabwe",
    "SOM": "somalia", "MOZ": "mozambique", "BFA": "burkina-faso", "MLI": "mali", "NER": "niger", "ETH": "ethiopia", "MDG": "madagascar", "CMR": "cameroon", "HTI": "haiti"}


def file_hash(path):
    with Path(path).open("rb") as h:
        return hashlib.file_digest(h, "sha256").hexdigest()


def row(iso, month, feature, value, unit, hashes, lag=1):
    return {"iso3": iso, "month": month, "feature": feature, "value": value, "unit": unit,
            "geography_level": "country", "source_sha256": hashes,
            "release_lag_months": lag, "availability_basis": "assumed_lag"}


def ports_monthly(path, countries, start, end):
    sums, counts, ports = defaultdict(float), defaultdict(int), defaultdict(set)
    seen = set()
    features = ("import_dry_bulk", "import_cargo", "export_cargo", "portcalls_cargo")
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        for r in csv.DictReader(handle):
            iso = r["ISO3"]
            month = f"{int(r['year']):04d}-{int(r['month']):02d}"
            if iso not in countries or not start <= month <= end:
                continue
            key = (iso, r["portid"], month, int(r["day"]))
            if key in seen:
                raise ValueError("Duplicate PortWatch port/day")
            seen.add(key)
            ports[iso, month].add(r["portid"])
            for f in features:
                if r[f] != "":
                    sums[iso, month, f] += float(r[f])
                    counts[iso, month, f] += 1
    digest = file_hash(path)
    result = []
    for (iso, month, f), value in sorted(sums.items()):
        y, m = map(int, month.split("-"))
        expected = len(ports[iso, month]) * calendar.monthrange(y, m)[1]
        # Partial monthly totals would confound missingness with shipping collapse.
        complete = counts[iso, month, f] == expected
        result.append(row(iso, month, "portwatch_" + f, value if complete else None,
                          "calls" if f.startswith("portcalls") else "metric_tons", [digest]))
    return result


def hdx_resource(slug, predicate, cache):
    meta, provenance = fetch_json("https://data.humdata.org/api/3/action/package_show?" + urlencode({"id": slug}), cache)
    if not meta.get("success"):
        raise ValueError(f"HDX dataset unavailable: {slug}")
    dataset = meta["result"]
    candidates = [r for r in dataset["resources"] if predicate(r)]
    if len(candidates) != 1:
        raise ValueError(f"Expected one matching resource for {slug}, found {len(candidates)}")
    path, download = fetch(candidates[0]["url"], cache)
    return path, {"dataset": slug, "license": dataset.get("license_title", dataset.get("license_id")),
                  "resource": candidates[0], "metadata_download": provenance, "download": download}


def acled_monthly(iso, slug, cache, start, end):
    import openpyxl
    path, meta = hdx_resource(("democratic-republic-of-congo" if iso == "COD" else slug) + "-acled-conflict-data",
        lambda r: "political_violence_events_and_fatalities" in r.get("name", "").lower(), cache)
    return parse_acled(iso, path, meta, start, end)


def parse_acled(iso, path, meta, start, end):
    import openpyxl
    # openpyxl checks extensions for paths; raw content-addressed blobs have none.
    with path.open("rb") as h:
        book = openpyxl.load_workbook(h, read_only=True, data_only=True)
        records = book["Data"].iter_rows(values_only=True)
        header = next(records)
        required = {"Year", "Month", "Events", "Fatalities"}
        if not required <= set(header):
            raise ValueError(f"ACLED schema changed: {header}")
        totals, seen = defaultdict(float), set()
        for values in records:
            r = dict(zip(header, values))
            month = f"{int(r['Year']):04d}-{datetime.strptime(str(r['Month']), '%B').month:02d}"
            if r.get("ISO3", iso) != iso or not start <= month <= end:
                continue
            key = (r.get("Admin1"), r.get("Admin2"), month)
            if key in seen:
                raise ValueError("Duplicate ACLED district-month")
            seen.add(key)
            for f in ("Events", "Fatalities"):
                if r[f] is None:
                    raise ValueError("Missing ACLED count cannot be interpreted as zero")
                totals[month, f] += float(r[f])
        meta["terms_of_use"] = [list(map(str, r)) for r in book["TOU"].iter_rows(values_only=True)]
        book.close()
    return [row(iso, m, "acled_" + f.lower(), v, "count", [meta["download"]["sha256"]])
            for (m, f), v in sorted(totals.items())], meta


def prices_monthly(iso, slug, cache, start, end):
    path, meta = hdx_resource("wfp-food-prices-for-" + slug,
        lambda r: r.get("format", "").lower() == "csv" and "food prices" in r.get("name", "").lower(), cache)
    return parse_prices(iso, path, meta, start, end)


def parse_prices(iso, path, meta, start, end):
    # Use USD prices where provided; never mix local currencies or package sizes.
    values = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as h:
        reader = csv.DictReader(h)
        if not {"date", "commodity", "unit", "pricetype", "usdprice"} <= set(reader.fieldnames or []):
            raise ValueError("WFP food price schema changed")
        for r in reader:
            if r["date"].startswith("#"):
                continue  # HDX HXL metadata row
            month = r["date"][:7]
            if start <= month <= end and r["usdprice"] and r["pricetype"] == "Retail":
                # Keep each exact commodity and unit in a separate channel.
                values[month, r["commodity"], r["unit"]].append(float(r["usdprice"]))
    result = [row(iso, m, f"wfp_price:{commodity}:{unit}", statistics.median(v),
                  "USD/" + unit, [meta["download"]["sha256"]]) for (m, commodity, unit), v in sorted(values.items())]
    return result, meta


def chirps_monthly(countries, start, end, cache):
    import numpy as np
    import rasterio
    from rasterio.mask import mask
    shapes, metadata = {}, []
    for iso in countries:
        info, provenance = fetch_json(f"https://www.geoboundaries.org/api/current/gbOpen/{iso}/ADM0/", cache)
        geometry, geom_meta = fetch_json(info["gjDownloadURL"], cache)
        shapes[iso] = [f["geometry"] for f in geometry["features"]]
        metadata.append({"boundary": info, "api": provenance, "geometry": geom_meta})
    sy, sm = map(int, start.split("-")); ey, em = map(int, end.split("-"))
    months = [f"{t//12:04d}-{t%12+1:02d}" for t in range(sy*12+sm-1, ey*12+em)]
    def process(month):
        url = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0." + month.replace("-", ".") + ".tif.gz"
        blob, provenance = fetch(url, cache)
        tif = cache / (provenance["sha256"] + ".tif")
        if not tif.exists():
            temp = tif.with_suffix(".partial")
            with gzip.open(blob, "rb") as source, temp.open("wb") as target:
                shutil.copyfileobj(source, target)
            temp.replace(tif)
        result = []
        with rasterio.open(tif) as src:
            if src.crs.to_epsg() != 4326:
                raise ValueError("Unexpected CHIRPS CRS")
            for iso, geometries in shapes.items():
                pixels, transform = mask(src, geometries, crop=True, filled=False)
                field = pixels[0]
                valid = ~np.ma.getmaskarray(field) & np.isfinite(field.data) & (field.data >= 0)
                latitude = transform.f + (np.arange(field.shape[0]) + 0.5) * transform.e
                weights = np.broadcast_to(np.cos(np.deg2rad(latitude))[:, None], field.shape)
                value = float(np.average(field.data[valid], weights=weights[valid])) if valid.any() else None
                boundary_hash = next(m["geometry"]["sha256"] for m in metadata if m["boundary"]["boundaryISO"] == iso)
                result.append(row(iso, month, "chirps_rainfall", value, "mm/month", [provenance["sha256"], boundary_hash], lag=2))
        # Retain compressed original; avoid 60 full global rasters on disk.
        tif.unlink()
        print(json.dumps({"rainfall_month": month, "countries": len(result)}), flush=True)
        return result, provenance
    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result, provenance in pool.map(process, months):
            rows.extend(result); metadata.append(provenance)
    return rows, metadata


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sources", nargs="+", choices=["ports", "acled", "prices", "rainfall"], required=True)
    p.add_argument("--countries", nargs="+", default=list(COUNTRIES))
    p.add_argument("--start", default="2018-01"); p.add_argument("--end", default="2023-12")
    p.add_argument("--ports-csv", type=Path)
    p.add_argument("--cache", type=Path, default=Path("data/raw/cache"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    rows, provenance, failures = [], [], []
    for source in args.sources:
        if source == "ports":
            if args.ports_csv:
                digest = file_hash(args.ports_csv)
                args.cache.mkdir(parents=True, exist_ok=True)
                path = args.cache / digest
                if not path.exists():
                    shutil.copyfile(args.ports_csv, path)
                meta = {"sha256": digest, "url": PORTS_URL, "origin": "handoff local download imported into durable cache",
                        "imported_at": datetime.now(timezone.utc).isoformat()}
            else:
                path, meta = fetch(PORTS_URL, args.cache)
            rows.extend(ports_monthly(path, args.countries, args.start, args.end)); provenance.append(meta)
        elif source == "rainfall":
            result, meta = chirps_monthly(args.countries, args.start, args.end, args.cache)
            rows.extend(result); provenance.extend(meta)
        else:
            function = acled_monthly if source == "acled" else prices_monthly
            for iso in args.countries:
                try:
                    result, meta = function(iso, COUNTRIES[iso], args.cache, args.start, args.end)
                    rows.extend(result); provenance.append(meta)
                    print(json.dumps({"source": source, "iso3": iso, "rows": len(result)}), flush=True)
                except Exception as error:
                    failures.append({"source": source, "iso3": iso, "error": str(error)})
                    print(json.dumps(failures[-1]), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    args.output.with_suffix(".manifest.json").write_text(json.dumps({"sha256": file_hash(args.output),
        "provenance": provenance, "failures": failures, "rows": len(rows),
        "limitations": ["Country signals broadcast to districts; not district measurements.",
                         "Release lags assumed, historical revisions not controlled.",
                         "Current boundaries used as fixed geographic aggregation masks."]}, indent=2))
    print(json.dumps({"rows": len(rows), "failures": len(failures)}))


if __name__ == "__main__":
    main()
