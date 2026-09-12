# Food Insecurity Forecasting — Data & Findings Handoff

Factual record of data inspected, measurements taken, and source-access tests run.
Working directory: `/Users/aabd/repos/food_data`

Project intent: fine-tune a Time-Series Language Model (OpenTSLM) to predict IPC food
insecurity phase from time-series inputs, emitting a natural-language rationale plus a
phase label.

---

## 1. Local data

### 1.1 `hfid_hv1.csv` (37 MB)

Harmonized food-insecurity panel. **Primary dataset.**

- 311,838 rows, 21 columns, monthly
- Date range 2007-01 → 2024
- 80 countries (`ADMIN0`), 6,214 distinct `(ADMIN0, ADMIN1, ADMIN2)` units
- 13 UN region groupings in `region`

Columns and non-null rates:

| Column | Non-null | Notes |
|---|---|---|
| `year_month`, `ADMIN0`, `ADMIN1` | 100% | |
| `ADMIN2` | 98.7% | |
| `ipc_phase_fews` | 44.4% | values {1,2,3,4,5} |
| `ha_fews` | 44.1% | values {0,1} |
| `ipc_phase_ipcch` | 31.3% | values {1,2,3,4,**6**} — 6 is outside the standard 1–5 CH scale, unresolved |
| `ha_ipcch` | 31.3% | |
| `set_ipcch` | 31.3% | constant 0.0 across all rows |
| `rfg_ipcch` | 31.3% | constant 0.0 across all rows |
| `fcs_lit` | 6.1% | |
| `rcsi_lit` | 5.1% | |
| `fcs_rt mean` / `max` / `min` | 39.2% | |
| `rcsi_rt mean` / `max` / `min` | 39.2% | |
| `iso2`, `iso3`, `region` | 100% | |

- `fcs_rt` / `rcsi_rt` values are in the 0–1 range (example row: 0.1933), not the raw
  FCS 0–112 scale. Normalization method not documented in the file.
- No P-codes. Admin units are name strings only (e.g. `` `Adan ``, apostrophe included).

### 1.2 `ALL_HFIC/` — FEWS NET shapefiles

Per-region, per-month "current situation" polygons.

| Folder | Prefix | Range | Files |
|---|---|---|---|
| Central America and the Caribbean | LAC | 2009-07 → 2022-10 | 356 |
| Central Asia | CA | 2009-07 → **2021-06** | 319 |
| East Africa | EA | 2009-07 → 2022-10 | 375 |
| Southern Africa | SA | 2009-07 → 2022-10 | 359 |
| West Africa | WA | 2009-07 → 2022-10 | 363 |

- Naming: `XX_YYYYMM_CS.{shp,shx,dbf,cpg,shp.xml}`
- DBF schema: `CS` (numeric) and, in files after 2011-03, `HA0` (0/1)
- Per `Readme.pdf`: `CS` after 2011-03 is IPC phase; before 2011-03 it is the FEWS NET
  Food Insecurity Severity Scale (FNFIS), different classification criteria.
  `HA0 = 1` means the phase would likely be at least one worse without humanitarian assistance.
- Geometry: POLYGON, GCS_WGS_1984 / EPSG:4326
- **Records are dissolved by phase**, not by admin unit. Each record is one multi-part
  polygon covering all areas of a given `CS`/`HA0` combination. `WA_202210_CS` has 5
  records total, bbox lon −12.24→24.00, lat 1.65→25.00.
- `.shp.xml` lineage confirms ArcGIS `Dissolve` applied to a source `HFIC_Data` geodatabase.
- Contains **no country or admin attribute** — country identity is not recoverable from
  these files without external boundary data.
- Also present: `FEWSNET_Legend.lyr`, `IPC_Legend.lyr`, `IPC_HumanitarianAssistance.lyr`, `Readme.pdf`

### 1.3 `2510.02410v3 (1).pdf`

OpenTSLM paper, 34 pages. Details in §4.

---

## 2. Measurements on `hfid_hv1.csv`

All computed directly from the file.

### 2.1 IPC publication cadence

Gaps between consecutive `ipc_phase_fews` values within an admin unit:

| Gap | Count |
|---|---|
| 2 months | 1,856 |
| 3 months | 54,352 |
| 4 months | 72,629 |
| 6 months | 2,258 |
| 8 months | 1,629 |
| 12 months | 778 |

**Consequence: no admin unit has a 12-month contiguous monthly IPC series. Zero such
windows exist in the file.** IPC phase is periodic (3–4 month cycle); `fcs_rt` and
`rcsi_rt` are monthly.

### 2.2 District-level windows

Criteria: trailing window of W months where `fcs_rt mean` and `rcsi_rt mean` are both
present for every month, and `ipc_phase_fews` is present at t+H.

| W | H | Samples |
|---|---|---|
| 12 | 0 | 17,066 |
| 12 | 3 | **15,593** |
| 12 | 6 | 13,693 |

Label distribution at W=12, H=3:

| Phase | Count | Share |
|---|---|---|
| 1 | 4,526 | 29.0% |
| 2 | 4,965 | 31.8% |
| 3 | 5,770 | 37.0% |
| 4 | 332 | 2.1% |
| 5 | 0 | 0% |

Country distribution (W=12, H=3): Yemen 3,984 · Nigeria 2,527 · Kenya 1,800 ·
Guatemala 1,760 · Malawi 1,486 · DR Congo 860 · Zimbabwe 540 · Somalia 518 ·
Mozambique 516 · Burkina Faso 315 · Mali 300 · Niger 252

Temporal distribution (year of window end): 2019 = 332 · 2020 = 996 · 2021 = 1,356 ·
2022 = 5,814 · 2023 = 7,095

**100% of W=12/H=3 windows end 2019-01 or later**, because the `fcs_rt`/`rcsi_rt` series
begins then.

### 2.3 Country-level aggregation

Aggregating districts to country-month:

- 42 countries present, 1,748 country-months
- 858 country-months have ≥1 IPC value; 1,035 have ≥1 FCS value

Sample counts requiring a complete country-level FCS/rCSI window:

| W | H | Gap-fill | Samples | Countries |
|---|---|---|---|---|
| 12 | 3 | no | 94 | 16 |
| 6 | 3 | no | 123 | 16 |
| 3 | 3 | no | 132 | 16 |
| 12 | 0–6 | no | 666 | 16 |
| 3 | 0–6 | yes | **942 (ceiling)** | 16 |

Country counts are identical (16) across every configuration. Yemen contributes 12 of
the 94 at W=12/H=3.

Label definitions tested at W=12/H=3 (94 samples):
- max phase across districts → {2: 4, 3: 63, 4: 27}
- rounded mean phase → {1: 18, 2: 56, 3: 20}
- binary, ≥20% of districts at phase 3+ → {0: 47, 1: 47}

---

## 3. External data sources

Access tested 2026-09-12.

### 3.1 IMF PortWatch — downloaded

- Catalog: `https://portwatch.imf.org/api/feed/dcat-us/1.1.json` (2,192 dataset entries)
- **Daily Ports Data**, item id `83b1bbc7b3354c5fb1f40673bb8f852e`
  CSV: `https://portwatch.imf.org/api/download/v1/items/83b1bbc7b3354c5fb1f40673bb8f852e/csv?layers=0`
- Downloaded: 649,027,881 bytes, 5,703,531 rows. Range **2019/01/01 → 2026/07/24**.
- Schema:
  ```
  date, year, month, day, portid, portname, country, ISO3,
  portcalls_container, portcalls_dry_bulk, portcalls_general_cargo,
  portcalls_roro, portcalls_tanker, portcalls_cargo, portcalls,
  import_container, import_dry_bulk, import_general_cargo, import_roro,
  import_tanker, import_cargo, import,
  export_container, export_dry_bulk, export_general_cargo, export_roro,
  export_tanker, export_cargo, export, ObjectId
  ```
  Import/export volumes are in metric tons. Derived from AIS satellite signals on ~90,000
  vessels; 2,065 ports covered; updated weekly (Tuesdays 09:00 ET).
- **Daily Chokepoints Data**, item id `3da2b9ca97684916b75c4013f95d18ab` — 28 chokepoints.
  Each value is one global figure per chokepoint per day; it takes the same value for every
  district and country within a given month (no cross-sectional variance).

Port coverage vs. mean monthly `import_dry_bulk` (metric tons), for countries present in
`hfid_hv1.csv`:

| Country | Ports | Mean monthly dry-bulk import |
|---|---|---|
| Nigeria | 29 | 1,088,848 |
| Kenya | 2 | 713,390 |
| Guatemala | 2 | 663,421 |
| Yemen | 9 | 566,796 |
| Djibouti | 1 | 421,826 |
| Mozambique | 5 | 401,947 |
| Tanzania | 4 | 359,573 |
| Honduras | 3 | 263,215 |
| Madagascar | 6 | 261,236 |
| Sudan | 3 | 251,316 |
| Haiti | 3 | 130,201 |
| Somalia | 5 | 87,375 |
| DR Congo | 6 | 42,064 |

No ports in dataset (landlocked): **Burkina Faso, Chad, Ethiopia, Malawi, Mali, Niger,
South Sudan, Zimbabwe**. Combined these account for ~2,893 of the 15,593 district samples
(~19%); countries with direct port coverage account for ~11,965 (~77%).

Port values are per-country: within one country, all districts receive the same value.

### 3.2 CHIRPS rainfall — open, verified

- `https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0.YYYY.MM.tif.gz`
- HTTP 200, no authentication. 14,489,865 bytes for `2023.01`.
- Directory listing current through `chirps-v2.0.2026.08.tif.gz`.
- 0.05° global grid, 1981–present. Requires zonal statistics against admin boundaries to
  produce per-district values.

### 3.3 ACLED conflict data

**Own API is gated:**
- `api.acleddata.com` — does not resolve (curl status 000)
- `https://acleddata.com/api/acled/read` → **403**
- `https://acleddata.com/oauth/token` → 405 on GET (endpoint exists, requires POST credentials)

**Open via HDX:** 421 ACLED datasets on `data.humdata.org`.
`yemen-acled-conflict-data` downloaded without authentication: 2,066,204 bytes XLSX.
Sheets `['TOU', 'Data']`. `Data` sheet: 46,954 rows × 10 columns, from 2015.

```
Country | Admin1 | Admin2 | ISO3 | Admin2 Pcode | Admin1 Pcode | Month | Year | Events | Fatalities
Yemen   | Taizz  | Al Misrakh | YEM | YE1511 | YE15 | January | 2015 | 0 | 0
```

Pre-aggregated to admin2 × month. Includes P-codes. Licence field on HDX reads "Other";
the TOU sheet carries ACLED's attribution terms. Point-level coordinates and event-type
detail are not in this aggregated version.

### 3.4 UCDP GED — gated

`https://ucdpapi.pcr.uu.se/api/gedevents/{25.1, 24.1, 23.1, 22.1}` all return **401**,
body: `API token required. Add header: x-ucdp-access-token: <your-token>`.

### 3.5 WFP food prices — open, verified

- HDX API: `https://data.humdata.org/api/3/action/package_search?q=wfp+food+prices` → 1,039 results
- Per-country datasets, e.g. `wfp-food-prices-for-yemen`, `wfp-food-prices-for-kenya`
- Each provides two CSV resources: a **Food Prices** file and a **Markets** file containing
  market coordinates.

### 3.6 WorldPop — open, verified

- `https://hub.worldpop.org/rest/data/pop/wpgp?iso3=YEM` → 21 records
- Returns direct raster URLs, e.g.
  `https://data.worldpop.org/GIS/Population/Global_2000_2020/2000/YEM/yem_ppp_2000.tif`

### 3.7 FEWS NET current regional coverage (from fews.net, 2026)

- East Africa: Burundi, Djibouti, Ethiopia, Kenya, Rwanda, Somalia, South Sudan, Sudan, Tanzania, Uganda
- West Africa: Benin, Burkina Faso, Cameroon, Central African Republic, Chad, Côte d'Ivoire, Guinea, Liberia, Mali, Mauritania, Niger, Nigeria, Senegal, Sierra Leone, Togo
- Southern Africa: Angola, DR Congo, Lesotho, Madagascar, Malawi, Mozambique, Zambia, Zimbabwe
- Asia (no standalone "Central Asia" grouping on the current site): Afghanistan, Nepal, Pakistan, Papua New Guinea, Sri Lanka, Tajikistan
- Latin America and the Caribbean: Colombia, Ecuador, El Salvador, Guatemala, Haiti, Honduras, Nicaragua, Venezuela

This is current coverage and does not necessarily match the 2009–2022 shapefile contents.

---

## 4. OpenTSLM (arXiv 2510.02410v3)

Repo: `github.com/OpenTSLM/OpenTSLM` (redirects from `StanfordBDHG/OpenTSLM`).

### 4.1 Architectures

- **OpenTSLM-SoftPrompt** — learnable time-series tokens concatenated with text tokens.
  VRAM scales with both series count and series length; paper reports OOM for large inputs.
- **OpenTSLM-Flamingo** — time series as a separate modality via cross-attention.
  VRAM mostly bound by the LLM backbone.

### 4.2 Sample structure (from source)

`QADataset._format_sample` builds:

```
PromptWithAnswer(
    TextPrompt(pre_prompt),                        # task instructions + label set
    [TextTimeSeriesPrompt(text, series), ...],     # one per 1-D channel
    TextPrompt(post_prompt),                       # e.g. "Rationale:"
    answer                                         # "<rationale> Answer: <label>"
)
```

`TextTimeSeriesPrompt` asserts the series is 1-dimensional, non-empty, numeric.
Subclasses implement `_load_splits`, `_get_answer`, `_get_pre_prompt`, `_get_post_prompt`,
`_get_text_time_series_prompt_list`. Reference implementation: `HARCoTQADataset`.

Series are rendered into the text prompt as:
`"The following is <description>, it has mean X and std Y:\n<values>"`

### 4.3 CoT dataset generation method (§A.2)

- Generator: **GPT-4o**, snapshot `gpt-4o-2024-08-06`, **temperature 0.3, seed 42**
- Input to generator: a **plot** of the series plus the **ground-truth label**
- The generator is shown **two** candidate labels — the correct one and a deliberately
  **dissimilar** distractor. At training and inference time the model is instead shown the
  **full** label set.
- Data plotted without normalization; multiple series rendered as subplots in one figure
- Prompt rules used verbatim:
  - analyze without assuming a specific label
  - think step-by-step
  - single natural paragraph, no bullets/numbered steps/headings
  - do not refer to the plot or to visual analysis
  - do not mention any class label until the final sentence
  - must end with `Answer: [CORRECT_LABEL]`
- QC: prompt engineering plus manual review of a subset
- Splits: 80/10/10 for all datasets

### 4.4 Dataset sizes (Table 4)

| Dataset | Train / Val / Test | Series | Length |
|---|---|---|---|
| TSQA | 38,400 / 4,800 / 4,800 | 1 | — |
| M4-Captions | 80,000 / 10,000 / 10,000 | 1 | 64–512 pts |
| HAR-CoT | 68,542 / 8,718 / 8,222 | 3 | 2.56 s @ 50 Hz |
| Sleep-CoT | 7,434 / 930 / 930 | 1 | 30 s @ 100 Hz |
| ECG-QA-CoT | 159,313 / 31,137 / 41,093 | 12 | 10 s @ 100 Hz |

### 4.5 Training configuration (§A.1.1)

AdamW · encoder LR 2e-4 · LoRA 2e-4 · cross-attention 2e-4 · projector 1e-4 ·
linear schedule with 10% warmup · gradient clipping ℓ2 = 1.0 · weight decay 0.01 ·
up to 200 epochs, early stopping patience 5.

### 4.6 Reported results (macro-F1)

| Task | OpenTSLM best | GPT-4o baseline |
|---|---|---|
| TSQA | 84.54 (82.06 acc) | 45.32 |
| HAR-CoT | 65.44 | 2.95 |
| Sleep-CoT | 54.40 (72.04 acc) | 15.47 |
| ECG-QA-CoT | 40.25 | 18.19 |

### 4.7 Limitations stated by the authors

- CoT datasets were generated by GPT-4o from plots, and GPT-4o performs poorly on those
  plots alone; the paper states curated datasets would likely yield better rationales.
- The model can produce a correct rationale with an incorrect final answer; the loss does
  not explicitly enforce answer correctness.
- SoftPrompt VRAM grows with series count and length, becoming impractical for long inputs.
- ECG-QA fine-tuning of tokenized baselines was infeasible at their sequence lengths.

---

## 5. Structural properties relevant to modelling

Stated as properties of the data, not as recommendations.

1. `ipc_phase_fews` is published on a 3–4 month cycle; `fcs_rt`/`rcsi_rt` are monthly. A
   monthly IPC input channel is not constructible from this file.
2. `hfid_hv1.csv` carries admin unit **names only, no P-codes**. ACLED (via HDX) carries
   P-codes. Joining the two requires either name matching or an external boundary set.
   The `ALL_HFIC` shapefiles cannot supply boundaries — they are dissolved by phase.
3. PortWatch port values are **country-level**: identical for every district within a
   country in a given month. PortWatch chokepoint values are **global**: identical for
   every district worldwide in a given month.
4. Port import volumes differ by orders of magnitude between countries (Nigeria 1,088,848 t
   vs. Somalia 87,375 t monthly mean) and carry seasonality.
5. `import_dry_bulk` includes non-food commodities (coal, ore, fertilizer, cement).
6. Phase 5 does not occur in any usable window. Phase 4 occurs in 332 of 15,593 (2.1%).
7. The five largest countries by sample count (Yemen, Nigeria, Kenya, Guatemala, Malawi)
   account for 74% of district samples.
8. District windows overlap in time within an admin unit; a random split places overlapping
   windows from the same unit in different partitions.
9. Sample counts in §2.2 require only `fcs_rt`/`rcsi_rt` completeness. Any additional
   channel made mandatory intersects this set downward.
10. Rainfall affects food security at harvest, on a lag tied to the growing-season calendar,
    which varies by country. FEWS NET publishes per-country seasonal calendars.

---

## 6. Environment

- Python 3.13 at `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13`
- Installed during this session: `pyshp`, `openpyxl`, `poppler` (via Homebrew, for `pdftotext`/`pdfinfo`)
- Not installed: `geopandas`, `gdal`/`ogrinfo`, `pandas`, `gh` CLI
- `ports.csv` (649 MB) and the paper text extract are in the session scratchpad:
  `/private/tmp/claude-501/-Users-aabd-repos-food-data/52bff3f4-c511-4ce4-90c3-73ab4825eea5/scratchpad/`
  Scratchpad contents are session-scoped and may not persist; the PortWatch CSV is
  re-downloadable from the URL in §3.1.
