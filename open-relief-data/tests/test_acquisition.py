from io import BytesIO
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import pytest
from open_relief_data.http import fetch
from open_relief_data.portwatch import query_url, fetch_daily
from open_relief_data.multimodal import ports_monthly


def test_query_escapes_and_bounds():
    url=query_url("https://example.com/0","YEM","2020-01-01","2020-01-03",1000,1000)
    query=parse_qs(urlparse(url).query)
    assert query["resultOffset"]==["1000"]
    assert "20200103" in query["where"][0]
    with pytest.raises(ValueError):query_url("https://x","YEM' OR 1=1","2020-01-01","2020-01-03",0,1000)


def test_partial_month_not_shipping_decline(tmp_path):
    p=tmp_path/"ports.csv"
    p.write_text("ISO3,year,month,day,portid,import_dry_bulk,import_cargo,export_cargo,portcalls_cargo\nYEM,2020,1,1,p,3,4,5,6\n")
    rows=ports_monthly(p,["YEM"],"2020-01","2020-01")
    assert len(rows)==4
    assert all(r["value"] is None for r in rows)


def test_download_cache_integrity(tmp_path,monkeypatch):
    class Response(BytesIO):
        headers={"Content-Length":"3"};url="https://example.com/data"
    monkeypatch.setattr("open_relief_data.http.urlopen",lambda *a,**k:Response(b"abc"))
    path,meta=fetch("https://example.com/data",tmp_path)
    assert path.read_bytes()==b"abc"
    monkeypatch.setattr("open_relief_data.http.urlopen",lambda *a,**k:pytest.fail("Cache should prevent request"))
    assert fetch("https://example.com/data",tmp_path)[1]==meta
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError,match="Corrupt"):fetch("https://example.com/data",tmp_path)
