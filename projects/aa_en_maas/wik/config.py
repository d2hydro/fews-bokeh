"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

import pandas as pd

TITLE = "Bokeh FEWS-REST client op WIK Aa en Maas"
SERVER = "localhost:5002"
URL = "http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/"
MAP_BUFFER = 1000
SEARCH_YEARS = 10
FILTER_PARENT = "Export_Hydronet"
FILTER_SELECTED = "Hydronet_Keten"
LOG_LEVEL = "DEBUG"
EXCLUDE_PARS = ["Dummy"]
