"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

import pandas as pd

TITLE = "Bokeh FEWS-REST client op WIK Aa en Maas"
SERVER = "localhost:5002"
URL = "http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/"
MAP_BUFFER = 1000
SEARCH_YEARS = 5
FILTER_MONTHS = 3
TIMESERIES_DAYS = 7
FILTER_PARENT = "Export_Hydronet"
FILTER_SELECTED = "Hydronet_Keten"
NOW = pd.Timestamp(year=2020, month=6, day=1)
LOG_LEVEL = "DEBUG"
EXCLUDE_PARS = ["Dummy"]
