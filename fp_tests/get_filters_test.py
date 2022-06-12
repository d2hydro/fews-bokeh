import sys
from pathlib import Path
import json
from config import api

parentdir = Path(__file__).parents[1]
sys.path.insert(0, parentdir.as_posix())

from fewspy.get_filters import get_filters

DATA_PATH = Path(__file__).parent / "data"

with open(DATA_PATH / "filters.json") as src:
    filter_reference = json.load(src)
filters = api.get_filters()


def test_to_refrence_set():
    assert filter_reference == filters
