# OpenRelief data connectors

An independently installable acquisition project with no dependency on OpenRelief modeling
code. Extract this directory into its own repository if desired. Four connectors implement
**the actual TimeNet `BaseConnector.download()` / `convert()` contract**, using the pinned
[official TimeNet source](https://github.com/OpenTSLM/TimeNet/tree/c39ca32b64ad0c89ea54093dbcb285c1a93eb006).

Install from the workspace root:

```sh
python -m pip install -e './open-relief-data[multimodal,timenet]'
```

When extracted, run `python -m pip install -e '.[multimodal,timenet]'` instead.
The TimeNet dependency currently requires Python 3.12; use that version for the full workflow.

## Native TimeNet / TimeF

Available modules under `open_relief_data.timenet_sources`: `portwatch`, `acled`,
`wfp_prices`, `chirps`. Each exports `CONNECTOR` and includes a dataset card. Download
returns provenance-bearing raw references; convert performs no network access and returns
an actual `TimeFDataset`. The CLI writes TimeF, reads it back, and verifies its integrity:

```sh
OPEN_RELIEF_COUNTRIES=YEM OPEN_RELIEF_START_MONTH=2020-01 \
OPEN_RELIEF_END_MONTH=2020-03 \
python -m open_relief_data.timef acled --output artifacts/timef
```

Replace `acled` with another source. Defaults cover the 16 configured countries and
2018-01 through 2023-12. Rainfall downloads global rasters and is much larger than the
other sources. `OPEN_RELIEF_PORTS_CSV` optionally supplies an existing PortWatch snapshot.

```python
from pathlib import Path
from open_relief_data.timenet_sources.acled import CONNECTOR

connector = CONNECTOR()
raw_refs = connector.download(Path('data/raw/cache'))
dataset = connector.convert(raw_refs)
```

Records are country-level; each signal retains its real calendar-month timestamps,
nullable numeric values, original units, source hashes and assumed release lags.
Calendar months use an irregular axis because they have different lengths. Neither
missing values nor missing calendar months become zero observations. The pinned TimeNet
implementation uses `TimeFWriter`, rather than a connector `store()` method.

These connectors are usable through these imports and our CLI. They have **not** been
published to TimeNet's registry or registered in the upstream discovery namespace.
Per-connector requirements identify this local distribution; install it from source before
using an isolated upstream worker. No unpublished PyPI package is assumed to exist.

## Generic acquisition API

A lightweight interface is also available without TimeNet:

```python
from pathlib import Path
from open_relief_data.connectors import FetchRequest, ACLEDConnector

result = ACLEDConnector().fetch(FetchRequest(
    countries=('YEM',), start_month='2020-01', end_month='2020-12',
    cache=Path('data/raw/cache'),
))
observations = [row.to_dict() for row in result.observations]
# Persist result.manifest with the observations.
```

Equivalent classes: `PortWatchConnector`, `WFPPricesConnector`, `CHIRPSConnector`.
The separate generic protocol is not itself the TimeNet SDK interface.

Bulk monthly acquisition:

```sh
python -m open_relief_data.multimodal --sources ports --output artifacts/monthly-ports.jsonl
python -m open_relief_data.multimodal --sources acled prices --output artifacts/monthly-conflict-prices.jsonl
python -m open_relief_data.multimodal --sources rainfall --output artifacts/monthly-rainfall.jsonl
```

The defaults fetch all 16 countries. For a fresh rebuild, pass these three outputs to
`python -m open_relief.enrich` in the modeling repository; the current workspace additionally
has separate country-extension files, which must not be joined to overlapping fresh outputs.

A small daily PortWatch request avoids downloading the full bulk CSV:

```sh
open-relief-data portwatch --iso3 YEM --start 2020-01-01 --end 2020-01-03 \
  --output artifacts/portwatch-pilot.jsonl
```

Use `--refresh` before the subcommand to fetch a new snapshot. This command can be scheduled,
storing dated outputs and manifests; no scheduler has been installed automatically.

## Data semantics and provenance

Raw downloads are immutable SHA-256 blobs with retrieval manifests, URL, ETag and
Last-Modified when supplied. Cache integrity is checked; retries are bounded. Monthly
research data assume a one-month release lag, two for CHIRPS. Actual historical publication
and revision histories are unavailable. The daily connector instead records retrieval time
for building a future archive. Preserve these distinctions in downstream forecasts.

PortWatch requires complete days per observed port-month before aggregation. Port coverage
can still change; cargo/dry bulk are not food-specific. Missing landlocked shipping is
unknown, not zero. ACLED supports national and district aggregate tables; full administrative
names identify duplicate district-month rows. WFP retains exact commodity/unit and retail
USD prices, aggregating market medians. CHIRPS uses geoBoundaries country polygons with
cosine-latitude area weighting. Country values do not imply district-level measurements.

Country batches report failures explicitly; the typed connectors fail closed. Adding a
country outside the registry requires a verified HDX slug. Add tests and a card when adding
a native connector; keep network I/O in `download()` and parsing in `convert()`.

Retain IMF terms, ACLED TOU, WFP metadata and geoBoundaries attribution with reused data.
Source access does not imply unrestricted redistribution. Raw HFID is not bundled with
this acquisition package, and no license for it is inferred.
