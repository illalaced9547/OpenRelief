"""Version-1 long-form observation contract, independent of target choice."""
from dataclasses import asdict, dataclass
from datetime import date, datetime
import math


@dataclass(frozen=True)
class Observation:
    source: str
    source_sha256: str
    geography_id: str
    geography_level: str
    feature: str
    event_time: str
    availability_time: str
    availability_basis: str
    value: float | None
    unit: str

    def __post_init__(self):
        event = date.fromisoformat(self.event_time)
        available = datetime.fromisoformat(self.availability_time.replace("Z", "+00:00"))
        if available.tzinfo is None:
            raise ValueError("availability_time must include timezone")
        if available.date() < event:
            raise ValueError("Observation cannot be available before its event date")
        if self.availability_basis not in ("published", "retrieved", "assumed_lag"):
            raise ValueError("Unknown availability basis")
        if self.geography_level not in ("global", "country", "admin1", "admin2", "port", "grid"):
            raise ValueError("Unknown geographic level")
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
            raise ValueError("source_sha256 must be a SHA-256 hex digest")
        if self.value is not None and (isinstance(self.value, bool) or not math.isfinite(self.value)):
            raise ValueError("Values must be finite or explicitly missing")
        if not all((self.source, self.geography_id, self.feature, self.unit)):
            raise ValueError("Observation identifiers and unit are required")

    def to_dict(self):
        return asdict(self)


def available_at(observations: list[Observation], cutoff: str) -> list[Observation]:
    instant = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("Cutoff must include timezone")
    return [o for o in observations
            if datetime.fromisoformat(o.availability_time.replace("Z", "+00:00")) <= instant
            and date.fromisoformat(o.event_time) <= instant.date()]
