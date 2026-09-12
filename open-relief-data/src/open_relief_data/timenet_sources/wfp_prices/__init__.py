from pathlib import Path
from ..base import NativeWFP


class Connector(NativeWFP):
    CARD = Path(__file__).with_name("dataset.yaml")


CONNECTOR = Connector
