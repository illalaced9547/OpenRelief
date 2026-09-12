from pathlib import Path
from ..base import NativeACLED


class Connector(NativeACLED):
    CARD = Path(__file__).with_name("dataset.yaml")


CONNECTOR = Connector
