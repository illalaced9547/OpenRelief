import copy
import csv
import json
from pathlib import Path

import pytest
from open_relief.derived import add_derived_channels
from open_relief.dataset import build_dataset
from open_relief.adapter import format_input
from open_relief.enrich import is_staple_feature


def test_staple_selection_excludes_services_and_price_prefix():
    assert is_staple_feature('wfp_price:Wheat flour:KG')
    assert is_staple_feature('wfp_price:Rice (imported):KG')
    assert not is_staple_feature('wfp_price:Milling cost (wheat):50 KG')
    assert not is_staple_feature('wfp_price:Fuel:liter')


def channel(name, values):
    return {"name": name, "values": values, "months": [f"2021-{i+1:02}" for i in range(len(values))],
            "availability_times": [f"2021-{i+2:02}-28T23:59:59Z" for i in range(len(values))],
            "unit": "units", "geography_level": "country"}


def test_derived_trailing_windows_and_missing_values():
    sample = {"channels": [channel("wfp_staple_price", [10, 20, 0, 40, None, 80]),
                           channel("acled_events", [1, 2, 3, None, 5, 6]),
                           channel("portwatch_import_cargo", [10, 20, 30, 40, 50, 60]),
                           channel("fcs_rt mean", [.1, .3, .2, .5, .6, .4])]}
    originals = copy.deepcopy(sample["channels"])
    add_derived_channels(sample)
    index = {c["name"]: c for c in sample["channels"]}
    assert index["wfp_staple_price_change_1m_pct"]["values"] == [None, 100, -100, None, None, None]
    assert index["wfp_staple_price_change_3m_pct"]["values"] == [None, None, None, 300, None, None]
    assert index["acled_events_sum_3m"]["values"] == [None, None, 6, None, None, None]
    assert index["portwatch_import_cargo_vs_previous_3m_pct"]["values"][3] == 100
    assert index["fcs_rt mean_change_3m"]["values"][3] == pytest.approx(.4)
    assert index["acled_events_sum_3m"]["availability_times"][2] == originals[1]["availability_times"][2]
    assert sample["channels"][:4] == originals
    changed = {"channels": copy.deepcopy(originals)}
    changed["channels"][2]["values"][-1] = 999999
    add_derived_channels(changed)
    other = {c["name"]: c for c in changed["channels"]}
    assert other["portwatch_import_cargo_vs_previous_3m_pct"]["values"][:-1] == index["portwatch_import_cargo_vs_previous_3m_pct"]["values"][:-1]


def test_ipc_history_uses_only_assessments_available_each_month(tmp_path):
    source = tmp_path / 'panel.csv'
    fields = ['iso3', 'ADMIN0', 'ADMIN1', 'ADMIN2', 'year_month', 'ipc_phase_fews', 'fcs_rt mean', 'rcsi_rt mean']
    with source.open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for year in range(2020, 2025):
            for month in range(1, 13):
                writer.writerow(dict(zip(fields, ['YEM', 'Yemen', 'A', 'B', f'{year}-{month:02}',
                                                  4 if (year, month) == (2021, 1) else 2, .3, .4])))
    output = tmp_path / 'built'
    build_dataset(source, Path('configs/experiment.json'), output)
    rows = [json.loads(line) for line in (output / 'inputs.jsonl').read_text().splitlines()]
    sample = next(r for r in rows if r['cutoff'].startswith('2021-07'))
    assert sample['geography'] == {'iso3': 'YEM', 'country': 'Yemen', 'admin1': 'A', 'admin2': 'B'}
    channels = {c['name']: c for c in sample['channels']}
    assert channels['month_of_year']['values'] == [1, 2, 3, 4, 5, 6]
    assert channels['ipc_last_known_phase']['values'][:3] == [2, 4, 2]
    assert channels['ipc_assessment_age']['values'] == [1] * 6
    assert not any('sin' in name or 'cos' in name for name in channels)
    assert 'answer' not in format_input(sample)


def test_annotation_budget_retains_unknown_charges_without_double_count(tmp_path):
    from open_relief.annotation import prior_spend, usage_cost
    usage = {'prompt_tokens': 1000, 'completion_tokens': 100}
    (tmp_path / 'a.response.json').write_text(json.dumps({'usage': usage}))
    (tmp_path / 'a.charge.json').write_text(json.dumps({'usd': .01}))
    (tmp_path / 'b.charge.json').write_text(json.dumps({'usd': .08}))
    (tmp_path / 'c.response.json').write_text(json.dumps({'usage': usage}))
    assert prior_spend(tmp_path) == pytest.approx(.09 + usage_cost(usage))


def test_annotation_distinguishes_rolling_and_cutoff_assessment_ages():
    from open_relief.annotation import request_payload
    from test_temporal import sample
    value = sample()
    value['last_available_phase'] = {'phase': 2, 'event_month': '2021-11', 'availability_time': value['cutoff']}
    value['channels'].append(dict(channel('ipc_assessment_age', [2, 3, 4]), months=['2021-09', '2021-10', '2021-11']))
    original = copy.deepcopy(value)
    payload = request_payload({'input': value, 'target': {'phase': 3, 'target_month': '2022-03', 'phase_change': 1, 'deteriorated': True}}, 'gpt-5.6-terra')
    context = json.loads(payload['messages'][1]['content'])['input']
    assert context['last_available_phase']['age_months_at_cutoff'] == 1
    assert context['ipc_assessment_timeline'][-1]['assessment_event_month'] == '2021-07'
    assert value == original
