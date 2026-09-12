import json
from pathlib import Path
import pytest
pytest.importorskip('timenet')
from timenet.connectors import BaseConnector
from timenet.reader import TimeFReader
from timenet.writer import TimeFWriter
from timenet.registry.version import DatasetVersion
from open_relief_data.timenet_sources.base import timef_monthly
from open_relief_data.timenet_sources.portwatch import CONNECTOR


def test_native_connector_contract_and_timef_roundtrip(tmp_path,monkeypatch):
    connector=CONNECTOR()
    assert isinstance(connector,BaseConnector)
    rows=[{'iso3':'YEM','month':m,'feature':'import_cargo','value':v,'unit':'metric_tons',
           'source_sha256':['a'*64],'release_lag_months':1,'availability_basis':'assumed_lag'}
          for m,v in [('2020-01',1.0),('2020-02',None),('2020-03',3.0)]]
    monkeypatch.setattr('open_relief_data.http.urlopen',lambda *a,**k:pytest.fail('Conversion must not access the network'))
    dataset=timef_monthly(connector.metadata(),rows,[{'source':'fixture'}])
    with TimeFWriter(tmp_path,dataset) as writer:writer.write()
    path=tmp_path/'openrelief/portwatch'/'0.1.0'
    with TimeFReader(DatasetVersion.open_local(path)) as reader:
        reader.verify();restored=reader.read()
        assert len(restored.records)==1
        record=next(iter(restored.records))
        assert record.time_series[0].to_arrow().to_pylist()==[1.0,None,3.0]
        offsets=record.time_series[0].time_offsets_us()
        assert int(offsets[1])==31*86400*1_000_000
        assert int(offsets[2])==60*86400*1_000_000  # leap-year February, not fixed 30 days
