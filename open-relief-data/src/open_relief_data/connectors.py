"""Public connector API for reusable time-series ingestion (TimeNet integration seam).

No existing external TimeNet SDK contract has been assumed. Integrators depend on
this typed protocol and versioned observation schema, not CLI implementation details.
"""
from dataclasses import dataclass
from datetime import date
import calendar
import hashlib
import json
from pathlib import Path
from typing import Protocol, runtime_checkable
from .schema import Observation
from .http import fetch
from .multimodal import COUNTRIES, PORTS_URL, ports_monthly, acled_monthly, prices_monthly, chirps_monthly


@dataclass(frozen=True)
class FetchRequest:
    countries: tuple[str, ...]
    start_month: str
    end_month: str
    cache: Path

    def __post_init__(self):
        first=date.fromisoformat(self.start_month+"-01")
        last=date.fromisoformat(self.end_month+"-01")
        if first>last or not self.countries:
            raise ValueError("Provide countries and an ordered monthly interval")
        if any(len(c)!=3 or not c.isupper() for c in self.countries):
            raise ValueError("Countries must use uppercase ISO3 codes")


@dataclass(frozen=True)
class ConnectorResult:
    observations: tuple[Observation, ...]
    manifest: dict


@runtime_checkable
class TimeSeriesConnector(Protocol):
    source_id: str
    def fetch(self, request: FetchRequest) -> ConnectorResult: ...


def month_end(month: str, lag: int=0):
    y,m=map(int,month.split("-"));y,m=divmod(y*12+m-1+lag,12)
    return date(y,m+1,calendar.monthrange(y,m+1)[1]).isoformat()


def standardize(source: str, rows: list[dict], provenance: list[dict]) -> ConnectorResult:
    observations=[]; seen=set()
    for row in rows:
        key=(row["iso3"],row["month"],row["feature"])
        if key in seen:raise ValueError(f"Duplicate connector observation: {key}")
        seen.add(key)
        digest=hashlib.sha256(json.dumps(sorted(row["source_sha256"])).encode()).hexdigest()
        observations.append(Observation(source,digest,row["iso3"],"country",row["feature"],
            month_end(row["month"]),month_end(row["month"],row["release_lag_months"])+"T23:59:59Z",
            "assumed_lag",row["value"],row["unit"]))
    return ConnectorResult(tuple(observations),{"schema_version":1,"source_id":source,
        "provenance":provenance,"raw_hash_sets":sorted({tuple(sorted(r["source_sha256"])) for r in rows}),
        "availability_policy":"retrospective assumed lag; use raw retrieval timestamps for strict historical availability",
        "geography":"country", "observations":len(observations)})


class PortWatchConnector:
    source_id="imf_portwatch_monthly"
    def __init__(self, csv_path: Path | None=None):self.csv_path=csv_path
    def fetch(self,request:FetchRequest)->ConnectorResult:
        if self.csv_path:
            path=self.csv_path; provenance={"url":PORTS_URL,"origin":"caller-provided snapshot"}
        else:path,provenance=fetch(PORTS_URL,request.cache)
        return standardize(self.source_id,ports_monthly(path,request.countries,request.start_month,request.end_month),[provenance])


class ACLEDConnector:
    source_id="acled_hdx_monthly"
    def fetch(self,request:FetchRequest)->ConnectorResult:
        rows=[];provenance=[]
        for iso in request.countries:
            result,meta=acled_monthly(iso,COUNTRIES[iso],request.cache,request.start_month,request.end_month)
            rows.extend(result);provenance.append(meta)
        return standardize(self.source_id,rows,provenance)


class WFPPricesConnector:
    source_id="wfp_prices_monthly"
    def fetch(self,request:FetchRequest)->ConnectorResult:
        rows=[];provenance=[]
        for iso in request.countries:
            result,meta=prices_monthly(iso,COUNTRIES[iso],request.cache,request.start_month,request.end_month)
            rows.extend(result);provenance.append(meta)
        return standardize(self.source_id,rows,provenance)


class CHIRPSConnector:
    source_id="chirps_monthly"
    def fetch(self,request:FetchRequest)->ConnectorResult:
        rows,provenance=chirps_monthly(request.countries,request.start_month,request.end_month,request.cache)
        return standardize(self.source_id,rows,provenance)


CONNECTORS={"portwatch":PortWatchConnector,"acled":ACLEDConnector,"wfp_prices":WFPPricesConnector,"chirps":CHIRPSConnector}
