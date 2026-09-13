# Source inventory and verified interfaces

Read `HANDOFF.md` for the original measurements. Unknown publication lags stay unknown.
“Open” describes tested access, not unrestricted redistribution rights.

| Source | Event range / cadence | Geography | Access and implementation role |
|---|---|---|---|
| HFID `refrences/hfid_hv1.csv` | Measured 2007-06–2024-05; monthly panel; IPC 3–4 monthly, FCS/rCSI monthly | Named ADMIN0/1/2, 80 countries | Local authoritative target/history; no publication timestamps or license documentation in CSV; audited in [`reports/hfid-audit.json`](../reports/hfid-audit.json) (initial 12-month input-window exploration) and [`reports/hfid-audit-6months.json`](../reports/hfid-audit-6months.json) (six-month input window actually shipped, see the dataset card's coverage section) |
| FEWS ALL_HFIC | Handoff: 2009-07–2022-10, Central Asia ends 2021-06; periodic current assessments | Dissolved phase polygons, not admin boundaries | Located in sibling `food_data/ALL_HFIC`; not a reproducible required local dependency; needs boundary overlay and pre-2011 scale exclusion |
| IMF PortWatch daily ports | Handoff downloaded 2019-01-01–2026-07-24, daily observations; weekly Tuesday updates | Ports, aggregate to country | Verified item and layer on 2026-09-12; connector implemented |
| IMF PortWatch chokepoints | Daily; exact available range must be queried | 28 global chokepoints per handoff | Item `3da2b9ca97684916b75c4013f95d18ab`; optional global context, no district variation |
| CHIRPS v2 rainfall | 1981–present, monthly finalized rasters; release lag unverified | 0.05° raster | Official UCSB download; zonal statistics require admin boundaries, no substitute invented |
| ACLED HDX aggregates | Yemen from 2015 per handoff; monthly; refresh per resource metadata | ADMIN2 with P-codes | Country XLSX with TOU/Data sheets; retain TOU; exact crosswalk required |
| ACLED direct | Coverage/account dependent | Event-level | Gated OAuth service; do not use old unresolved hostname |
| UCDP GED | Version-dependent; lag unknown | Geocoded events | Handoff API returned 401 requiring token; optional comparison, no access bypass |
| WFP food prices | Country/resource-dependent monthly histories; refresh varies | Markets and admin names | HDX country CSV plus markets coordinates; stratify commodity/currency/unit/price type before aggregation |
| WorldPop | Queried series 2000–2020, annual; newer products distinct | Population raster | Official API and raster URLs; optional lagged population weights, not a label |
| FEWS seasonal calendars/current coverage | Country-specific calendars, current regional coverage 2026 | Country/region | Qualitative rainfall/harvest context; current coverage is not historical coverage |
| OpenTSLM paper/checkpoints | Research artifacts, not forecasting observations | N/A | Official project, paper and HF model cards inspected |

## Official URLs

- PortWatch catalog: https://portwatch.imf.org/api/feed/dcat-us/1.1.json
- Ports item metadata: https://www.arcgis.com/sharing/rest/content/items/83b1bbc7b3354c5fb1f40673bb8f852e?f=pjson
- Resolved layer: https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0
- Bulk CSV: https://portwatch.imf.org/api/download/v1/items/83b1bbc7b3354c5fb1f40673bb8f852e/csv?layers=0
- PortWatch methods: https://portwatch.imf.org/pages/data-and-methodology
- PortWatch item links its license to https://www.imf.org/external/terms.htm
- CHIRPS: https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/
- ACLED HDX metadata: https://data.humdata.org/api/3/action/package_show?id=yemen-acled-conflict-data
- WFP HDX metadata: https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-yemen
- WorldPop: https://hub.worldpop.org/rest/data/pop/wpgp?iso3=YEM
- UCDP: https://ucdpapi.pcr.uu.se/api/gedevents/25.1
- FEWS: https://fews.net
- OpenTSLM code: https://github.com/OpenTSLM/OpenTSLM
- Website: https://www.opentslm.com
- Paper: https://arxiv.org/abs/2510.02410 (local v3 PDF inspected)
- SP: https://huggingface.co/OpenTSLM/llama-3.2-1b-tsqa-sp
- Flamingo: https://huggingface.co/OpenTSLM/llama-3.2-1b-tsqa-flamingo
- Annotation API: https://developers.openai.com/api/docs/guides/structured-outputs

The live PortWatch layer has maximum 1,000 records/query, pagination and order-by support,
and `date` is DateOnly. The connector filters verified integer year/month/day fields.
Raw port imports represent all dry bulk, not food imports specifically.

## OpenTSLM findings

Pinned source commit: `2968f4b891baab4307f7e9d0043e87677b593a30`.
Official sample dictionaries contain parallel lists of 1-D numeric series and descriptions.
Collation pads to a multiple of patch size (current default 4) and mutates the input sample.
Six monthly points are padded to eight positions, requiring two patches/channel;
checkpoint encoder configuration must be inspected rather than trusting a global default.
The paper describes [-1,1] inputs with original scale in text; current collation optionally
z-scores instead. Choose/document one input-only transform explicitly and use it identically
before and after fine-tuning. Do not upsample months into synthetic daily detail.

SP concatenates projected series tokens with language; Flamingo uses a separate series
modality with cross-attention and a resampler. SP is a reasonable short-input candidate,
not a measured winner. Both official TSQA 1B checkpoint pages exist; the Flamingo card's
example mistakenly uses the SP repository ID and legacy imports, so use current source.
Backbones can require Hugging Face access; run official checkpoints on CUDA (or CPU),
not MPS. No local training or full checkpoint download is planned.

## Final implementation notes

The configured acquisition covers 16 countries. ACLED source tables vary between national
and district aggregates; the modeling inputs use national monthly totals. WFP selects the
best-covered training-period staple commodity and exact package unit, excluding services
such as wheat milling costs. CHIRPS v2 rasters are aggregated to countries using fixed
geoBoundaries gbOpen ADM0 polygons; actual values and provenance are cached locally.
HFID and national signals assume one-month release lags, except CHIRPS at two months.
These assumptions do not recover missing historical release or revision records.

Actual TimeNet source: https://github.com/OpenTSLM/TimeNet/tree/c39ca32b64ad0c89ea54093dbcb285c1a93eb006
Documentation: https://docs.timenet.ai/
Native connectors implement BaseConnector download/convert and produce TimeFDataset,
with TimeFWriter/TimeFReader round-trip verification. They are not published upstream.

Annotation uses gpt-5.6-terra, selected for cost and quality after rejecting GPT-4o for the
final workflow. Model reference: https://developers.openai.com/api/docs/models/gpt-5.6-terra
The cost guard charges conservatively at $2.50/M input tokens and $12/M output tokens,
without cache-read discounts, and reserves a byte-based input ceiling plus maximum output
for requests whose usage is unknown. Check current pricing before changing the model.
