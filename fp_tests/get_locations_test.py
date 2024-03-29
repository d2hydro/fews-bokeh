import sys
from pathlib import Path
import geopandas as gpd
from config import api

parentdir = Path(__file__).parents[1]
sys.path.insert(0, parentdir.as_posix())

from fewspy.get_locations import get_locations

ATTRIBUTES = ["MPN_IDENT", "MPN_BRON"]
DATA_PATH = Path(__file__).parent / "data"

locations_reference = gpd.read_file(DATA_PATH / "locations.gpkg").set_index(
    "location_id"
    )
locations = api.get_locations(attributes=ATTRIBUTES)


def test_to_refrence_set():
    cols = [i for i in locations.columns if i != "geometry"]
    assert locations[cols].sort_index().equals(
        locations_reference[cols].sort_index()
        )
