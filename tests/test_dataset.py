import copy
import json
from pathlib import Path
from open_relief.dataset import assign_split, validate_config, month_index
from open_relief.enrich import enrich
from open_relief.dataset import digest_file


def test_multinational_split_freezes_labels():
    c=json.loads(Path('configs/experiment.json').read_text());validate_config(c)
    assert assign_split(month_index('2022-07'),month_index('2022-10'),c)=='train'
    assert assign_split(month_index('2022-11'),month_index('2023-02'),c) is None
    assert assign_split(month_index('2023-03'),month_index('2023-06'),c)=='validation'
    assert assign_split(month_index('2023-07'),month_index('2023-10'),c) is None
    assert assign_split(month_index('2023-11'),month_index('2024-02'),c)=='test'


def test_optional_covariate_unavailable_at_cutoff_is_masked(tmp_path):
    from test_temporal import sample
    root=tmp_path/'core';root.mkdir()
    s=sample();s['geography']['iso3']='YEM'
    (root/'inputs.jsonl').write_text(json.dumps(s)+'\n');(root/'targets.jsonl').write_text('{}\n')
    manifest={'dataset_version':'v','config':{'train_end':'2021-12'},'counts':{'train':1},'files':{n:digest_file(root/n) for n in ('inputs.jsonl','targets.jsonl')}}
    (root/'manifest.json').write_text(json.dumps(manifest))
    monthly=tmp_path/'monthly.jsonl';monthly.write_text(json.dumps({'iso3':'YEM','month':'2021-11','feature':'chirps_rainfall','value':9.0,'unit':'mm','source_sha256':['a'*64],'release_lag_months':2})+'\n')
    out=tmp_path/'output';enrich(root,[monthly],out)
    r=json.loads((out/'inputs.jsonl').read_text())
    rainfall=next(c for c in r['channels'] if c['name']=='chirps_rainfall')
    assert rainfall['values']==[None,None,None]
