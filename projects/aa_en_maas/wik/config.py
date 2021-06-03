"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

import pandas as pd
from pathlib import Path

config_dir = Path(__file__).parent
TITLE = "Web-client op WIK Aa en Maas"
URL = "http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/"
MAP_BUFFER = 1000
SEARCH_YEARS = 5
FILTER_MONTHS = 3
TIMESERIES_DAYS = 7
FILTER_PARENT = "WIK_App"
FILTER_SELECTED = "WIK_Keten"
APP_FILTERS = ["WIK_Keten", "WIK_Oppervlaktewater", "WIK_Grondwater"]
BOUNDS = [ 564270, 6678290, 673280, 6769590]
LOG_LEVEL = "DEBUG"
EXCLUDE_PARS = ["Dummy", "P.radar.cal.early", "P.radar.cal.realtime"]
LOG_FILE = config_dir.joinpath(
    "..\..", "log", f"log_{pd.Timestamp.now().strftime('%Y%m%dT%H%M%S')}.txt").resolve()