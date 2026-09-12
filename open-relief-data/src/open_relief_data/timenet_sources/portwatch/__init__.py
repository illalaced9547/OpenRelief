from pathlib import Path
from ..base import NativePortWatch


class Connector(NativePortWatch):
    CARD = Path(__file__).with_name("dataset.yaml")


CONNECTOR = Connector
