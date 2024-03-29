import sys
from pathlib import Path
import pandas as pd
from config import api

parentdir = Path(__file__).parents[1]
sys.path.insert(0, parentdir.as_posix())

from fewspy.get_qualifiers import get_qualifiers


DATA_PATH = Path(__file__).parent / "data"

qualifiers_reference = pd.read_csv(DATA_PATH / "qualifiers.csv").set_index("id")
qualifiers = api.get_qualifiers()


def test_to_refrence_set():
    assert qualifiers.sort_index().equals(qualifiers_reference.sort_index())
