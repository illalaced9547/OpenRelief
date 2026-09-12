from pathlib import Path
from ..base import NativeCHIRPS


class Connector(NativeCHIRPS):
    CARD = Path(__file__).with_name("dataset.yaml")


CONNECTOR = Connector
