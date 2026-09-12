"""Future-aware historical supervision, kept outside forecasting inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import json
import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .dataset import load_examples
from .audit import month_index, month_string


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provenance: Literal["observed", "retrieved", "model_recalled", "inference"]
    statement: str
    channels: list[str]
    event_months: list[str]
    source_url: str | None
    uncertainty: str


class InteractionClaim(BaseModel):
    """A hypothesis explicitly connecting >=2 different-domain signals, not a single-channel fact."""
    model_config = ConfigDict(extra="forbid")
    provenance: Literal["model_recalled", "inference"]
    statement: str
    mechanism: str
    channels: list[str]
    event_months: list[str]
    source_url: str | None
    uncertainty: str


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_future_phase: int = Field(ge=1, le=5)
    precursor_patterns: list[Claim]
    interaction_hypotheses: list[InteractionClaim]
    rationale: str
    uncertainty: str
    confidence: float = Field(ge=0, le=1)


# Channel name prefix -> broad real-world signal domain, for enforcing cross-domain interactions.
SOURCE_DOMAINS = (
    ("portwatch", "shipping_trade"),
    ("acled", "conflict"),
    ("chirps", "rainfall"),
    ("wfp", "price"),
    ("fcs_rt", "food_consumption"),
    ("rcsi_rt", "coping_behavior"),
    ("ipc", "food_security_assessment"),
    ("last_available_phase", "food_security_assessment"),
    ("month_of_year", "calendar"),
)


def channel_domain(name: str) -> str:
    return next((domain for prefix, domain in SOURCE_DOMAINS if name.startswith(prefix)), "other")


SYSTEM = """You annotate historical food-security episodes for research supervision.
The supplied future phase is objective ground truth: copy it, never relabel it.
Describe concise precursor patterns and temporal ordering from the supplied input.
You may use confident internal historical knowledge, marking it model_recalled.
Distinguish observed data, retrieved evidence, recalled context and inference.
No retrieval tools are provided: never invent retrieved evidence or URLs.
FCS/rCSI are HFID normalized [0,1] series with unknown normalization; do not claim
raw food-consumption thresholds or assume an undocumented direction of severity.
STRICT: an increasing or decreasing HFID FCS/rCSI number must NEVER be described as
worsening/improving food consumption or increasing/decreasing coping behavior. Only
state the numeric direction. Describe food-security change from the supplied IPC
phase_change, not from the unknown index normalization. In the rationale clearly
separate measured numeric patterns from plausible interpretations of other channels.
Do not invent shipping, rainfall or conflict observations absent from the channels.
Cargo and dry-bulk imports are not food-specific. National signals are not district measurements.
ipc_last_known_phase month stamps are as-of months, not dates of new assessments.
ipc_assessment_age is measured at each series month, not at the later cutoff.
Use last_available_phase.event_month for the actual latest assessment date.
The latest assessment at the cutoff can be newer than every entry in the rolling
input window. Never transfer a rolling IPC age to last_available_phase. The supplied
ipc_assessment_timeline explicitly resolves the event date behind each rolling point;
last_available_phase.age_months_at_cutoff separately gives the latest assessment age.
Explain uncertainty; correlation and plausible mechanisms do not establish causation.
Give a short evidence summary, not a detailed hidden chain of thought. The rationale
is retrospective supervision, not an input available to a forecaster. Confidence
is annotation confidence, not a calibrated event probability.

precursor_patterns are single-domain facts (one channel or a tightly related group, e.g.
one price series and its own percentage-change derivatives). interaction_hypotheses are
different: each one must connect signals from at least two distinct real-world domains
(shipping/trade, conflict, rainfall, price, food_consumption, coping_behavior,
food_security_assessment) into one concrete, plausible compounding mechanism, e.g. a
conflict rise coinciding with a rainfall deficit and a price increase jointly reducing
market supply and purchasing power. State the mechanism explicitly in `mechanism`, keep
`statement` to the concrete numeric pattern being connected, and mark provenance
model_recalled only for genuine recalled historical context, otherwise inference. Never
mark an interaction hypothesis observed: combining channels is analysis, not direct
observation. Provide at least one interaction_hypotheses entry for every annotation, and
still explicitly flag it as a plausible hypothesis, not a proven causal chain."""


def request_payload(example: dict, model: str) -> dict:
    context = {"input": {k: example["input"][k] for k in ("geography", "cutoff", "horizon_months", "last_available_phase")},
               "target": {k: example["target"][k] for k in ("phase", "target_month", "phase_change", "deteriorated")}}
    context["input"]["channels"] = [{k: c[k] for k in ("name", "unit", "geography_level", "months", "values")} for c in example["input"]["channels"]]
    latest = context["input"]["last_available_phase"]
    if latest is not None:
        context["input"]["last_available_phase"] = dict(latest,
            age_months_at_cutoff=month_index(example["input"]["cutoff"][:7]) - month_index(latest["event_month"]))
    age_channel = next((c for c in example["input"]["channels"] if c["name"] == "ipc_assessment_age"), None)
    if age_channel:
        context["input"]["ipc_assessment_timeline"] = [
            {"as_of_month": month, "assessment_event_month": month_string(month_index(month) - age) if age is not None else None,
             "age_months_at_as_of_month": age}
            for month, age in zip(age_channel["months"], age_channel["values"])]
    for channel, original in zip(context["input"]["channels"], example["input"]["channels"]):
        if "description" in original:
            channel["description"] = original["description"]
    schema = Annotation.model_json_schema()
    channel_names = [c["name"] for c in example["input"]["channels"]] + ["last_available_phase"]
    schema["$defs"]["Claim"]["properties"]["channels"]["items"]["enum"] = channel_names
    schema["$defs"]["Claim"]["properties"]["provenance"]["enum"] = ["observed", "model_recalled", "inference"]
    schema["$defs"]["InteractionClaim"]["properties"]["channels"]["items"]["enum"] = channel_names
    return {"model": model, "messages": [{"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(context, sort_keys=True)}],
        "reasoning_effort": "medium", "max_completion_tokens": 4096,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "historical_annotation", "strict": True, "schema": schema}}}


def validate_annotation(value: dict, example: dict) -> Annotation:
    annotation = Annotation.model_validate(value)
    if annotation.observed_future_phase != example["target"]["phase"]:
        raise ValueError("Annotation changed objective label")
    channels = {c["name"] for c in example["input"]["channels"]} | {"last_available_phase"}
    months = {m for c in example["input"]["channels"] for m in c["months"]}
    # Historical annotation may legitimately refer to the observed future outcome.
    months.add(example["target"].get("target_month", ""))
    if example["input"].get("last_available_phase"):
        months.add(example["input"]["last_available_phase"]["event_month"])
    ages = next((c for c in example["input"]["channels"] if c["name"] == "ipc_assessment_age"), None)
    if ages:
        months.update(month_string(month_index(month) - age)
                      for month, age in zip(ages["months"], ages["values"]) if age is not None)
    for claim in annotation.precursor_patterns:
        if claim.provenance == "retrieved":
            raise ValueError("No retrieval evidence was supplied to this annotation run")
        if not set(claim.channels) <= channels:
            raise ValueError("Annotation references unavailable channel")
        if claim.provenance == "observed" and not set(claim.event_months) <= months:
            raise ValueError("Observed claim references a month outside the input window")
        if claim.source_url is not None:
            raise ValueError("Source URLs require a separate retrieval-enabled workflow")
    if not annotation.interaction_hypotheses:
        raise ValueError("At least one cross-domain interaction hypothesis is required")
    for claim in annotation.interaction_hypotheses:
        if not set(claim.channels) <= channels:
            raise ValueError("Annotation references unavailable channel")
        if claim.source_url is not None:
            raise ValueError("Source URLs require a separate retrieval-enabled workflow")
        if len({channel_domain(name) for name in claim.channels}) < 2:
            raise ValueError("Interaction hypothesis must span at least two distinct signal domains")
    return annotation


def select_pilot(examples, limit):
    """Exercise different transitions and countries in the small live pipeline test."""
    chosen, countries = [], set()
    categories = (lambda d: d is not None and d > 0,
                  lambda d: d is not None and d < 0,
                  lambda d: d == 0,
                  lambda d: d is None)
    for category in categories:
        candidate = next((e for e in examples if category(e["target"]["phase_change"])
                          and e["input"]["geography"]["iso3"] not in countries), None)
        if candidate is not None and len(chosen) < limit:
            chosen.append(candidate)
            countries.add(candidate["input"]["geography"]["iso3"])
    selected_ids = {e["input"]["sample_id"] for e in chosen}
    for distinct in (True, False):
        for e in examples:
            if len(chosen) >= limit:
                return chosen
            if e["input"]["sample_id"] in selected_ids:
                continue
            country = e["input"]["geography"]["iso3"]
            if distinct and country in countries:
                continue
            chosen.append(e)
            countries.add(country)
            selected_ids.add(e["input"]["sample_id"])
    return chosen


def usage_cost(usage):
    """Conservative Terra estimate: full cache-write rate and no read discounts."""
    return (usage.get("prompt_tokens", 0) * 2.5 + usage.get("completion_tokens", 0) * 12) / 1e6


def maximum_cost(payload):
    return ((len(json.dumps(payload).encode()) + 1000) * 2.5 + 4096 * 12) / 1e6


def prior_spend(cache):
    """Retain reservations for ambiguous API failures across process restarts."""
    charges = {p.name.removesuffix(".charge.json"): json.loads(p.read_text())["usd"]
               for p in cache.glob("*.charge.json")}
    for path in cache.glob("*.response.json"):
        key = path.name.removesuffix(".response.json")
        if key not in charges:
            charges[key] = usage_cost(json.loads(path.read_text()).get("usage") or {})
    return sum(charges.values())


def annotate(example: dict, model: str, cache: Path, client) -> dict:
    payload = request_payload(example, model)
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{key}.json"
    if path.exists():
        result = json.loads(path.read_text())
        validate_annotation(result["annotation"], example)
        result["sample_id"] = example["input"]["sample_id"]
        result["dataset_version"] = example["input"]["dataset_version"]
        return result
    raw_path = cache / f"{key}.response.json"
    unresolved_prior_charge = 0.0
    if raw_path.exists():
        from openai.types.chat import ChatCompletion
        response = ChatCompletion.model_validate(json.loads(raw_path.read_text()))
    else:
        charge_path = cache / f"{key}.charge.json"
        if charge_path.exists():
            unresolved_prior_charge = json.loads(charge_path.read_text())["usd"]
        charge_path.write_text(json.dumps({"usd": unresolved_prior_charge + maximum_cost(payload), "basis": "reserved_before_request"}))
        response = client.chat.completions.create(**payload)
    (cache / f"{key}.response.json").write_text(response.model_dump_json(indent=2) + "\n")
    if response.usage:
        if not unresolved_prior_charge and (cache / f"{key}.charge.json").exists() and raw_path.exists():
            # Retain any accumulated reservation from a previous ambiguous retry.
            previous = json.loads((cache / f"{key}.charge.json").read_text())
            if previous.get("basis") == "conservative_usage":
                unresolved_prior_charge = max(0, previous["usd"] - usage_cost(response.usage.model_dump()))
        (cache / f"{key}.charge.json").write_text(json.dumps({"usd": unresolved_prior_charge + usage_cost(response.usage.model_dump()), "basis": "conservative_usage"}))
    choice = response.choices[0]
    if choice.finish_reason != "stop" or choice.message.refusal or not choice.message.content:
        raise ValueError("Annotation refused, empty or truncated; no valid artifact cached")
    annotation = validate_annotation(json.loads(choice.message.content), example)
    result = {"sample_id": example["input"]["sample_id"], "dataset_version": example["input"]["dataset_version"],
        "purpose": "training_supervision_only", "request_sha256": key, "model": response.model,
        "request_id": response.id, "usage": response.usage.model_dump() if response.usage else {},
        "annotation": annotation.model_dump()}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(path)
    return result


def main():
    from dotenv import load_dotenv
    from openai import OpenAI
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--all", action="store_true", help="Annotate every training example, subject to budget")
    parser.add_argument("--output", type=Path, default=Path("artifacts/annotations-pilot.jsonl"))
    parser.add_argument("--cache", type=Path, default=Path("artifacts/annotation-cache"))
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--budget-usd", type=float, default=190.0)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if not 0 < args.budget_usd <= 190:
        parser.error("--budget-usd must be positive and at most 190 (reserve remains for pilots)")
    # One writer prevents concurrent runs from spending the same budget or cache entry.
    import fcntl
    args.cache.mkdir(parents=True, exist_ok=True)
    run_lock = (args.cache / ".run.lock").open("a")
    try:
        fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("Another annotation run owns this cache; wait for it to finish")
    load_dotenv()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if base_url != "https://api.openai.com/v1":
        parser.error("This run is authorized for the official OpenAI API only")
    model = os.getenv("OPENAI_ANNOTATION_MODEL", "gpt-5.6-terra")
    if not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is missing; configure .env")
    examples = load_examples(args.dataset, "train")
    # Deterministic diverse ordering instead of taking adjacent overlapping windows.
    examples.sort(key=lambda e: e["input"]["sample_id"])
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    if model != "gpt-5.6-terra":
        parser.error("Cost guard is verified for gpt-5.6-terra; update pricing before changing model")
    selected = examples if args.all else select_pilot(examples, args.limit)
    # UTF-8 bytes bound ordinary text token count; include schema and protocol overhead.
    # No automatic retries: ambiguous network failures must not multiply reserved spend.
    bound = sum(((len(json.dumps(request_payload(e,model)).encode()) + 1000) * 2.5 + 4096 * 12) / 1_000_000 for e in selected)
    print(json.dumps({"requests":len(selected), "conservative_cost_bound_usd":round(bound,2)}),flush=True)
    client = OpenAI(base_url=base_url, timeout=120, max_retries=0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results, failures = [], []
    spent, reserved = prior_spend(args.cache), 0.0
    starting_spend = spent
    pending = iter(selected)
    deferred = None
    budget_exhausted = False
    with args.output.open("w") as handle, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        exhausted = False
        while futures or not exhausted:
            while len(futures) < args.workers and not exhausted:
                example = deferred if deferred is not None else next(pending, None)
                deferred = None
                if example is None:
                    exhausted = True
                    break
                payload = request_payload(example, model)
                key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                cached = (args.cache / f"{key}.json").exists() or (args.cache / f"{key}.response.json").exists()
                ceiling = 0.0 if cached else maximum_cost(payload)
                if spent + reserved + ceiling > min(args.budget_usd,190):
                    deferred = example
                    if not futures:
                        budget_exhausted = True
                        exhausted = True
                    break
                futures[pool.submit(annotate,example,model,args.cache,client)] = (example,ceiling)
                reserved += ceiling
            if not futures:
                break
            done,_ = wait(futures,return_when=FIRST_COMPLETED)
            for future in done:
                example,ceiling=futures.pop(future); reserved-=ceiling
                try:
                    result=future.result();results.append(result)
                    if ceiling:
                        spent+=usage_cost(result["usage"])
                    handle.write(json.dumps(result)+"\n");handle.flush()
                except Exception as error:
                    spent+=ceiling  # reserve worst case when usage is unavailable
                    failures.append({"sample_id":example["input"]["sample_id"],"error":str(error)})
                completed=len(results)+len(failures)
                if completed % 25 == 0 or completed == len(selected):
                    print(json.dumps({"completed":completed,"valid":len(results),"failures":len(failures),"accounted_cost_usd":round(spent,4)}),flush=True)
    results.sort(key=lambda r:r["sample_id"])
    args.output.write_text("".join(json.dumps(r)+"\n" for r in results))
    args.output.with_suffix(".manifest.json").write_text(json.dumps({"requested":len(selected),"valid":len(results),"budget_exhausted":budget_exhausted,"accounted_cost_usd":spent,
        "prior_cache_spend_usd": starting_spend, "new_run_accounted_cost_usd": spent - starting_spend,
        "failures":failures,"model":model,"conservative_cost_bound_usd":bound,
        "estimated_usage_usd":sum(usage_cost(r["usage"]) for r in results),
        "pricing_source":"https://developers.openai.com/api/docs/models/gpt-5.6-terra", "cached_usage_may_include_previous_runs":True},indent=2)+"\n")
    if budget_exhausted:
        raise SystemExit("Run budget reached; completed annotations retained")
    if failures:
        raise SystemExit(f"{len(failures)} annotations failed validation or API access; see manifest and rerun to reuse cache")


if __name__ == "__main__":
    main()
