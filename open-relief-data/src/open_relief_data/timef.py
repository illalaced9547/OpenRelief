"""Build a native TimeF source dataset without publishing to a remote registry."""
import argparse
import importlib
import json
from pathlib import Path


def main():
    from timenet.writer import TimeFWriter
    from timenet.reader import TimeFReader
    from timenet.registry.version import DatasetVersion
    p=argparse.ArgumentParser()
    p.add_argument('source',choices=['portwatch','acled','wfp_prices','chirps'])
    p.add_argument('--cache',type=Path,default=Path('data/raw/cache'))
    p.add_argument('--output',type=Path,default=Path('artifacts/timef'))
    a=p.parse_args()
    cls=importlib.import_module('open_relief_data.timenet_sources.'+a.source).CONNECTOR
    connector=cls()
    references=connector.download(a.cache)
    dataset=connector.convert(references)
    with TimeFWriter(a.output,dataset) as writer:writer.write()
    path=a.output/dataset.metadata.dataset_id/str(dataset.metadata.dataset_version)
    with TimeFReader(DatasetVersion.open_local(path)) as reader:
        reader.verify()
        restored=reader.read()
        count=len(restored.records)
    print(json.dumps({'version_path':str(path),'records':count,'verified_round_trip':True}))


if __name__=='__main__':main()
