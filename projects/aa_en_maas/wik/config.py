"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

import pandas as pd
from pathlib import Path
from bokeh.models import BBoxTileSource

config_dir = Path(__file__).parent
TITLE = "Web-client op WIK Aa en Maas"
URL = "http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/"
MAP_BUFFER = 1000
SEARCH_YEARS = 5
FILTER_MONTHS = 12
TIMESERIES_DAYS = 7
FILTER_PARENT = "Export_Hydronet"
#FILTER_PARENT = "WIK_App"
FILTER_API = "Export_Hydronet"
APP_FILTERS = ["WIK_Keten", "WIK_Oppervlaktewater", "WIK_Grondwater"]
BOUNDS = [564270, 6678000, 673280, 6770000]
LOG_LEVEL = "DEBUG"
EXCLUDE_PARS = ["Dummy", "P.radar.cal.early", "P.radar.cal.realtime"]
LOG_FILE = config_dir.joinpath(
    "..\..", "log", f"log_{pd.Timestamp.now().strftime('%Y%m%dT%H%M%S')}.txt").resolve()
FILTER_COLORS = {"WIK_KET_Neerslag": {"fill": "lightblue", "line": "blue"},
                 "WIK_KET_Rioolgemaal": {"fill": "orange", "line": "black"},
                 "WIK_KET_RWZI": {"fill": "lightgreen", "line": "green"},
                 "Hydronet_Deurne": {"fill": "lightgrey", "line": "red"},
                 "Hydronet_Gemert-Bakel": {"fill": "yellow", "line": "green"},
                 "Hydronet_Helmond": {"fill": "pink", "line": "red"},
                 "Hydronet_Laarbeek": {"fill": "pink", "line": "black"},
                 "Hydronet_Kwartier": {"fill": "red", "line": "blue"},
                 "WIK_OW_Kwaliteit": {"fill": "lightgreen", "line": "blue"},
                 "Grondwater_Automatisch": {"fill": "orange", "line": "blue"},
                 "WIK_GW_DINO": {"fill": "lightblue", "line": "black"}}

TILE_SOURCES = {
    "rwzi": {"url": (
        "https://maps.aaenmaas.nl/services/wms?"
        "service=WMS&version=1.3.0&request=GetMap&layers=DAMO_S:RWZI"
        "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
        "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
        "class": BBoxTileSource,
        "visible": True},
    "hoofdrioolgemaal": {"url": (
            "https://maps.aaenmaas.nl/services/wms?"
            "service=WMS&version=1.3.0&request=GetMap&layers=LCMS_afvalwater:RIOOLGEMAAL"
            "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
            "class": BBoxTileSource,
            "visible": True},
    "overstortconstructie": {"url": (
            "https://maps.aaenmaas.nl/services/DAMO_S/ows?"
            "service=WMS&version=1.3.0&request=GetMap&layers=WS_RIOOLOVERSTORT"
            "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
            "class": BBoxTileSource,
            "visible": False},
    "leidingtrace": {"url": (
            "https://maps.aaenmaas.nl/services/wms?"
            "service=WMS&version=1.3.0&request=GetMap&layers=LCMS_afvalwater:LEIDINGSEGMENT"
            "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
            "class": BBoxTileSource,
            "visible": False},
    "watergangen": {"url": (
            "https://maps.aaenmaas.nl/services/wms?"
            "service=WMS&version=1.3.0&request=GetMap&layers=DAMO_S:HYDROOBJECT"
            "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
            "class": BBoxTileSource,
            "visible": False},
    "rioleringsdeelgebied": {"url": (
            "https://maps.aaenmaas.nl/services/DAMO_S/ows?"
            "service=WMS&version=1.3.0&request=GetMap&layers=WS_RIOLERINGSGEBIED"
            "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
            "class": BBoxTileSource,
            "visible": False,
			"alpha": 0.5},
    "waterschapsgrens": {"url": (
            "https://maps.aaenmaas.nl/services/wms?"
            "service=WMS&version=1.3.0&request=GetMap&layers=LCMS:GRE_WATERSCHAP"
            "&width=265&height=265&styles=&crs=EPSG:3857&format=image/png&transparent=true"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
            "class": BBoxTileSource,
            "visible": True}
    }

FILTER_RELATIONS = {"WIK_KET_Rioolgemaal": "RIOLERINGSDISTRICT",
					"Hydronet_Deurne": "RIOLERINGSDISTRICT",
                    "Hydronet_Gemert-Bakel": "RIOLERINGSDISTRICT",
                    "Hydronet_Helmond": "RIOLERINGSDISTRICT",
                    "Hydronet_Laarbeek": "RIOLERINGSDISTRICT"}