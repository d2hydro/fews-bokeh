"""
Module for calling the FEWS REST API.

The module contains one class and methods corresponding with the FEWS PI-REST requests:
https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service#FEWSPIRESTWebService-GETtimeseries
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests
from fewsbokeh.time import Timer

_GEODATUM_MAPPING = {"WGS 1984": "epsg:4326", "Rijks Driehoekstelsel": "epsg:28992"}

_REQUEST_PARAMETERS_ALLOWED = {
    "timeseries": [
        "locationIds",
        "startTime",
        "endTime",
        "filterId",
        "parameterIds",
        "qualifierIds",
        "documentVersion",
        "thinning",
        "onlyHeaders",
        "showStatistics"
    ]
}

class Api:
    """
    FEWS PI-REST api it needs an server url and a logger.

    All variables related to PI-REST variables are defined camelCase. All others are
    snake_case.
    """

    def __init__(self, url, logger, filterId):
        self.document_format = "PI_JSON"
        self.url = url
        self.parameters = None
        self.locations = None
        self.logger = logger
        self.timer = Timer(logger)
        self._get_parameters(filterId)

    def _get_parameters(self, filterId):
        rest_url = f"{self.url}parameters"
        parameters = dict(filterId=filterId,
                          documentFormat=self.document_format)
        self.timer.reset()
        response = requests.get(rest_url, parameters)
        print(response.url)
        self.timer.report("Parameters request")
        if response.status_code == 200:
            if "timeSeriesParameters" in response.json().keys():
                par_df = pd.DataFrame(response.json()["timeSeriesParameters"])
                par_df.set_index("id", inplace=True)
                self.parameters = par_df
                result = par_df
            else:
                result = None
            self.timer.report("Parameters parsed")
        else:
            self.logger.error(f"FEWS Server responds {response.text}")
        return result

    def get_filters(self, filterId=None):
        """Get filters as dictionary, or sub-filters if a filterId is specified."""
        rest_url = f"{self.url}filters"

        parameters = {"documentFormat": self.document_format, "filterId": filterId}
        self.timer.reset()
        response = requests.get(rest_url, parameters)
        self.timer.report("Filters request")
        if response.status_code == 200:
            if "filters" in response.json().keys():
                filters = {
                    item["id"]: {
                        key: value for key, value in item.items() if not key == "id"
                    }
                    for item in response.json()["filters"]
                }
                result = filters
            else:
                self.logger.warning('no filter returned')
                result = None
        self.timer.report("Filters parsed")
        return result

    def get_headers(self, filterId, endTime, parameterIds=None, locationIds=None):
        """Get parameters. FilterId is required. A list of locations optional."""
        result = None

        if not parameterIds:
            parameterIds = self.parameters.index.to_list()
        timeseries = self.get_timeseries(
            filterId=filterId,
            locationIds=locationIds,
            startTime=endTime,
            endTime=endTime,
            parameterIds=parameterIds,
            onlyHeaders=True,
            showStatistics=True
        )

        if "timeSeries" in timeseries.keys():
            result = [ts['header'] for ts in timeseries["timeSeries"]]

            # ids = list(set([
            #     series["header"]["parameterId"] for series in timeseries["timeSeries"]])
            #     )
            # timesteps = {item: [] for item in ids}
            # for series in timeseries["timeSeries"]:
            #     parameter_id = series["header"]["parameterId"]
            #     timesteps[parameter_id] += [series["header"]["timeStep"]]
            # timesteps = {key: list(map(dict, set(tuple(sorted(
            #     d.items())) for d in value))) for key, value in timesteps.items()}

            # qualifiers = {item: [] for item in ids}
            # for series in timeseries["timeSeries"]:
            #     parameter_id = series["header"]["parameterId"]
            #     if "qualifierId" in series["header"].keys():
            #         qualifiers[parameter_id] += [series["header"]["qualifierId"]]
            # qualifiers = {key: [
            #     list(x) for x in set(tuple(x) for x in value)]
            #     for key, value in qualifiers.items()}

        else:
            self.logger.warning(
                f"no timeSeries in filter {filterId} for locations {locationIds}"
            )
            result = None

        return result

    def to_parameter_names(self, parameterIds):
        """Convert parameterIds to names."""
        return self.parameters.loc[parameterIds]["name"].to_list()

    def to_parameter_ids(self, names):
        """Convert parameterIds to parameterIds."""
        return self.parameters.loc[self.parameters["name"].isin(names)].index.to_list()

    def get_locations(self, showAttributes=False, filterId=None):
        """Get location en return as a GeoDataFrame."""
        rest_url = f"{self.url}locations"

        parameters = dict(
            documentFormat=self.document_format,
            showAttributes=showAttributes,
            filterId=filterId,
        )
        self.timer.reset()
        response = requests.get(rest_url, parameters)
        self.timer.report("Locations request")
        if response.status_code == 200:
            gdf = gpd.GeoDataFrame(response.json()["locations"])
            gdf["geometry"] = gdf.apply(
                (lambda x: Point(float(x["x"]), float(x["y"]))), axis=1
            )
            gdf.crs = _GEODATUM_MAPPING[response.json()["geoDatum"]]
            gdf = gdf.to_crs("epsg:3857")
            gdf["x"] = gdf["geometry"].x
            gdf["y"] = gdf["geometry"].y
            drop_cols = [
                col
                for col in gdf.columns
                if col
                not in [
                    "locationId",
                    "description",
                    "shortName",
                    "parentLocationId",
                    "x",
                    "y",
                    "geometry",
                ]
            ]
            gdf = gdf.drop(drop_cols, axis=1)
            gdf.index = gdf["locationId"]

            self.locations = gdf
            self.timer.report("Locations parsed")
        return gdf

    def get_timeseries(
        self,
        filterId,
        locationIds=None,
        startTime=None,
        endTime=None,
        parameterIds=None,
        qualifierIds=None,
        documentVersion=None,
        thinning=None,
        onlyHeaders=False,
        unreliables=False,
        showStatistics=False
    ):
        """Get timeseries within a filter, optionally filtered by other variables."""
        result = None
        rest_url = f"{self.url}timeseries"
        #print(f"thinning: {thinning}")
        parameters = {
            key: value
            for key, value in locals().items()
            if value and (key in _REQUEST_PARAMETERS_ALLOWED["timeseries"])
        }

        parameters.update({"documentFormat": self.document_format})
        self.timer.reset()
        #print(parameters)
        response = requests.get(rest_url, parameters)
        self.logger.debug(response.url)
        if response.status_code == 200:
            if onlyHeaders:
                self.timer.report("Timeseries headers request")
                result = response.json()
            elif "timeSeries" in response.json().keys():
                self.timer.report("TimeSeries request")
                result = []
                for time_series in response.json()["timeSeries"]:
                    ts = {}
                    if "header" in time_series.keys():
                        ts["header"] = time_series["header"]
                    if "events" in time_series.keys():
                        df = pd.DataFrame(time_series["events"])
                        if not unreliables:
                            df = df.loc[pd.to_numeric(df["flag"]) < 6]
                        df["datetime"] = pd.to_datetime(df["date"]) + pd.to_timedelta(
                            df["time"]
                        )
                        df["value"] = pd.to_numeric(df["value"])
                        df = df.loc[
                            df["value"] != pd.to_numeric(ts["header"]["missVal"])
                        ]
                        df = df.drop(
                            columns=[
                                col
                                for col in df.columns
                                if col not in ["datetime", "value"]
                            ]
                        )
                        ts["events"] = df
                    result += [ts]
                result = response.json()["timeZone"], result
                self.timer.report("TimeSeries parsed")
            else:
                self.logger.info("returning emtpy timeseries")
                result = response.json()
        else:
            self.logger.error(
                f"server responded with error ({response.status_code}): {response.text}"
                f"url send to the server was: {response.url}"
            )
        if result is None:
            self.logger.warning("method returns None")

        return result
