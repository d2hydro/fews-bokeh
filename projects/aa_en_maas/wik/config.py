"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

import pandas as pd

TITLE = "Bokeh FEWS-REST client op WIK Aa en Maas"
SERVER = "localhost:5002"
URL = "http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/"
MAP_BUFFER = 1000
START_TIME = pd.Timestamp(year=2019, month=1, day=1)
END_TIME = pd.Timestamp.now()
FILTER_PARENT = "Export_Hydronet"
FILTER_SELECTED = "Hydronet_Keten"
LOG_LEVEL = "DEBUG"
