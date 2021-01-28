"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

import pandas as pd
from pathlib import Path

config_dir = Path(__file__).parent
TITLE = "Bokeh FEWS-REST client op WIK Aa en Maas"
SERVER = "localhost:5002"
URL = "http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/"
MAP_BUFFER = 1000
SEARCH_YEARS = 5
FILTER_MONTHS = 3
TIMESERIES_DAYS = 7
FILTER_PARENT = "Export_Hydronet"
FILTER_SELECTED = "Hydronet_Keten"
LOG_LEVEL = "DEBUG"
EXCLUDE_PARS = ["Dummy", "P.radar.cal.early", "P.radar.cal.realtime"]
LOG_FILE = config_dir.joinpath(
    "..", "log", f"log_{pd.Timestamp.now().strftime('%Y%m%dT%H%M%S')}.txt").resolve()
