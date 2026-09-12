"""Native TimeNet connectors: I/O-only download, network-free convert."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor

from timenet.connectors import BaseConnector
from timenet.dataset import TimeFDataset, TimeSeries
from timenet.dataset.axis import IrregularAxis
from timenet.types import TimeSeriesSpec, Annotation

from open_relief_data.http import fetch, fetch_json
from open_relief_data.multimodal import (COUNTRIES, PORTS_URL, file_hash, hdx_resource,
    ports_monthly, parse_acled, parse_prices, row)


@dataclass(frozen=True)
class RawRef:
    path: Path
    kind: str
    metadata: dict
    iso3: str | None = None


def stable_id(*parts):
    return hashlib.sha256(json.dumps(parts,sort_keys=True,default=str).encode()).hexdigest()[:32]


def timef_monthly(metadata, rows, raw_provenance):
    """One record per country; explicit timestamps accommodate unequal calendar months."""
    import pyarrow as pa
    dataset=TimeFDataset(metadata=metadata)
    countries=defaultdict(lambda:defaultdict(list))
    seen=set()
    for r in rows:
        key=(r['iso3'],r['feature'],r['month'])
        if key in seen:raise ValueError(f'Duplicate monthly record {key}')
        seen.add(key);countries[r['iso3']][r['feature']].append(r)
    for iso,features in sorted(countries.items()):
        anchor=datetime.fromisoformat(min(r['month'] for values in features.values() for r in values)+'-01').replace(tzinfo=timezone.utc)
        streams=[];availability={};units={};hashes={}
        for feature,values in sorted(features.items()):
            values.sort(key=lambda r:r['month'])
            original_unit=values[0]['unit']
            unit={'metric_tons':'metric_ton','mm/month':'millimeter','count':'dimensionless','calls':'dimensionless'}.get(original_unit,'dimensionless')
            spec=TimeSeriesSpec(spec_type='signal_'+stable_id(feature,original_unit)[:16],name=feature,
                unit_value=unit,dtype='float64',nullable=True)
            offsets=[int((datetime.fromisoformat(r['month']+'-01').replace(tzinfo=timezone.utc)-anchor).total_seconds()*1_000_000) for r in values]
            data=[r['value'] for r in values]
            # Load Arrow lazily; no accidental conversion of null to a real zero.
            axis=IrregularAxis.spanning(offsets)
            streams.append(TimeSeries(spec=spec,signal=feature,time_axis=axis,n_values=len(data),
                loader=lambda values=tuple(data):pa.array(values,type=pa.float64()),
                time_offsets_loader=lambda offsets=tuple(offsets):pa.array(offsets,type=pa.int64()),
                source_id=iso,time_series_id=stable_id(metadata.dataset_id,iso,feature,values)))
            availability[feature]=[{'month':r['month'],'release_lag_months':r['release_lag_months'],'basis':r['availability_basis']} for r in values]
            units[feature]=original_unit;hashes[feature]=sorted({h for r in values for h in r['source_sha256']})
        record=dataset.add_record(time_series=tuple(streams),subject_ids=(iso,),record_id=stable_id(metadata.dataset_id,iso),start_time=anchor)
        for key,value in [('geography',{'iso3':iso,'level':'country'}),('availability',availability),
                          ('original_units',units),('source_hashes',hashes),('provenance',raw_provenance)]:
            record.add_annotation(Annotation(key=key,value=value,id=stable_id(metadata.dataset_id,iso,key)))
    dataset.derive_schema()
    return dataset


class SourceConnector(BaseConnector[RawRef]):
    """Environment-configured source range shared by the concrete native connectors."""
    def __init__(self):
        super().__init__()
        self.countries=tuple(os.getenv('OPEN_RELIEF_COUNTRIES',','.join(COUNTRIES)).split(','))
        self.start=os.getenv('OPEN_RELIEF_START_MONTH','2018-01')
        self.end=os.getenv('OPEN_RELIEF_END_MONTH','2023-12')
        if self.start>self.end:raise ValueError('Inverted source interval')


class NativePortWatch(SourceConnector):
    def download(self,cache_dir):
        local=os.getenv('OPEN_RELIEF_PORTS_CSV')
        if local:
            source=Path(local);digest=file_hash(source);cache_dir.mkdir(parents=True,exist_ok=True)
            path=cache_dir/digest
            if not path.exists():shutil.copyfile(source,path)
            metadata={'url':PORTS_URL,'sha256':digest,'origin':'caller supplied source snapshot'}
        else:path,metadata=fetch(PORTS_URL,cache_dir)
        return [RawRef(path,'ports',metadata)]
    def convert(self,raw_refs):
        if len(raw_refs)!=1:raise ValueError('Expected one ports CSV')
        ref=raw_refs[0]
        return timef_monthly(self.metadata(),ports_monthly(ref.path,self.countries,self.start,self.end),[ref.metadata])


class NativeACLED(SourceConnector):
    def download(self,cache_dir):
        refs=[]
        for iso in self.countries:
            slug='democratic-republic-of-congo' if iso=='COD' else COUNTRIES[iso]
            path,meta=hdx_resource(slug+'-acled-conflict-data',
                lambda r:'political_violence_events_and_fatalities' in r.get('name','').lower(),cache_dir)
            refs.append(RawRef(path,'acled',meta,iso))
        return refs
    def convert(self,raw_refs):
        rows=[];provenance=[]
        for ref in raw_refs:
            result,meta=parse_acled(ref.iso3,ref.path,dict(ref.metadata),self.start,self.end)
            rows.extend(result);provenance.append(meta)
        return timef_monthly(self.metadata(),rows,provenance)


class NativeWFP(SourceConnector):
    def download(self,cache_dir):
        refs=[]
        for iso in self.countries:
            path,meta=hdx_resource('wfp-food-prices-for-'+COUNTRIES[iso],
                lambda r:r.get('format','').lower()=='csv' and 'food prices' in r.get('name','').lower(),cache_dir)
            refs.append(RawRef(path,'wfp',meta,iso))
        return refs
    def convert(self,raw_refs):
        rows=[];provenance=[]
        for ref in raw_refs:
            result,meta=parse_prices(ref.iso3,ref.path,ref.metadata,self.start,self.end)
            rows.extend(result);provenance.append(meta)
        return timef_monthly(self.metadata(),rows,provenance)


class NativeCHIRPS(SourceConnector):
    def download(self,cache_dir):
        refs=[]
        for iso in self.countries:
            info,api=fetch_json(f'https://www.geoboundaries.org/api/current/gbOpen/{iso}/ADM0/',cache_dir)
            path,meta=fetch(info['gjDownloadURL'],cache_dir)
            refs.append(RawRef(path,'boundary',{'boundary':info,'download':meta,'api':api},iso))
        sy,sm=map(int,self.start.split('-'));ey,em=map(int,self.end.split('-'))
        months=[f'{t//12:04d}-{t%12+1:02d}' for t in range(sy*12+sm-1,ey*12+em)]
        def download(month):
            path,meta=fetch('https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0.'+month.replace('-','.')+'.tif.gz',cache_dir)
            return RawRef(path,'rainfall',{'month':month,'download':meta})
        with ThreadPoolExecutor(max_workers=3) as pool:refs.extend(pool.map(download,months))
        return refs
    def convert(self,raw_refs):
        import numpy as np
        import rasterio
        from rasterio.io import MemoryFile
        from rasterio.mask import mask
        shapes={};hashes={}
        for ref in raw_refs:
            if ref.kind=='boundary':
                shapes[ref.iso3]=[f['geometry'] for f in json.loads(ref.path.read_text())['features']]
                hashes[ref.iso3]=ref.metadata['download']['sha256']
        rows=[]
        for ref in raw_refs:
            if ref.kind!='rainfall':continue
            with gzip.open(ref.path,'rb') as handle, MemoryFile(handle.read()) as memory, memory.open() as src:
                if src.crs.to_epsg()!=4326:raise ValueError('Unexpected rainfall CRS')
                for iso,geometry in shapes.items():
                    pixels,transform=mask(src,geometry,crop=True,filled=False)
                    field=pixels[0];valid=~np.ma.getmaskarray(field)&np.isfinite(field.data)&(field.data>=0)
                    lat=transform.f+(np.arange(field.shape[0])+0.5)*transform.e
                    weights=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],field.shape)
                    value=float(np.average(field.data[valid],weights=weights[valid])) if valid.any() else None
                    rows.append(row(iso,ref.metadata['month'],'chirps_rainfall',value,'mm/month',
                        [ref.metadata['download']['sha256'],hashes[iso]],lag=2))
        return timef_monthly(self.metadata(),rows,[r.metadata for r in raw_refs])
