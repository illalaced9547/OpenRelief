import copy
import json
from pathlib import Path
import pytest
from open_relief.audit import month_index, month_string
from open_relief.dataset import assign_split, validate_config
from open_relief.adapter import format_input, format_training
from open_relief.evaluate import parse_prediction, score
from open_relief.annotation import validate_annotation
from open_relief_data.schema import Observation, available_at


def sample():
    return {"sample_id":"s", "dataset_version":"v", "split":"train", "cutoff":"2021-12-31T23:59:59Z",
            "horizon_months":3,"last_available_phase":None,
            "geography":{"iso3":"YEM","country":"Yemen","admin1":"A","admin2":"B"},
            "channels":[{"name":"rainfall","unit":"mm","geography_level":"country",
                "months":["2021-09","2021-10","2021-11"],"values":[2.0,None,4.0],
                "availability_times":["2021-10-31T23:59:59Z",None,"2021-12-31T23:59:59Z"]}]}


def test_month_arithmetic():
    assert month_string(month_index("2021-12")+3)=="2022-03"
    with pytest.raises(ValueError):month_index("2021-13")


def test_split_purges_label_release_crossing_boundary():
    c=json.loads(Path("configs/experiment.json").read_text())
    c.update(train_end="2021-12", validation_start="2022-01", validation_end="2022-12", test_start="2023-01", test_end="2023-12")
    validate_config(c)
    assert assign_split(month_index("2021-08"),month_index("2021-11"),c)=="train"
    assert assign_split(month_index("2021-09"),month_index("2021-12"),c) is None
    assert assign_split(month_index("2022-09"),month_index("2022-12"),c) is None
    assert assign_split(month_index("2023-12"),month_index("2024-03"),c)=="test"


def test_forecasting_prompt_has_no_answer_and_does_not_mutate():
    s=sample(); original=copy.deepcopy(s)
    out=format_input(s)
    assert "answer" not in out
    assert out["time_series"]==[[-1.0,0.0,1.0],[1.0,0.0,1.0]]
    out["time_series"][0][0]=500
    assert s==original


def test_future_available_values_rejected():
    s=sample();s["channels"][0]["availability_times"][2]="2022-01-31T23:59:59Z"
    with pytest.raises(ValueError,match="leaked"):format_input(s)


def test_training_target_separate():
    e={"input":sample(),"target":{"phase":4}}
    out=format_training(e,"<eos>")
    assert json.loads(out["answer"].removesuffix("<eos>"))["phase"]==4
    assert "observed_future_phase" not in out["pre_prompt"]


def test_annotations_cannot_relabel():
    a={"observed_future_phase":3,"precursor_patterns":[],"rationale":"Unknown","uncertainty":"High","confidence":0.1}
    with pytest.raises(ValueError,match="label"):validate_annotation(a,{"input":sample(),"target":{"phase":4}})


def test_invalid_output_is_not_dropped():
    assert parse_prediction('{"phase":true,"rationale":"x"}') is None
    assert parse_prediction('{"phase":6,"rationale":"x"}') is None
    metrics=score([{"true_phase":3,"predicted_phase":0},{"true_phase":3,"predicted_phase":3}])
    assert metrics["accuracy"]==0.5
    assert metrics["invalid_rate"]==0.5


def test_retrieved_data_cannot_enter_historical_forecast():
    o=Observation("ports","a"*64,"YEM","country","imports","2020-01-01","2026-09-12T12:00:00Z","retrieved",12.0,"tonnes")
    assert available_at([o],"2020-02-01T00:00:00Z")==[]
    assert available_at([o],"2026-09-13T00:00:00Z")==[o]
    with pytest.raises(ValueError):available_at([o],"2026-09-13")
