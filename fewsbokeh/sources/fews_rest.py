"""
Module for calling the FEWS REST API.

The module contains one class and methods corresponding with the FEWS PI-REST requests:
https://publicwiki.deltares.nl/display/FEWSDOC/FEWS+PI+REST+Web+Service#FEWSPIRESTWebService-GETtimeseries
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests

_GEODATUM_MAPPING = {"WGS 1984": "epsg:4326", "Rijks Driehoekstelsel": "epsg:28992"}

_REQUEST_PARAMETERS_ALLOWED = {
    "timeseries": [
        "locationIds",
        "startTime",
        "endTime",
        "filterId",
        "parameterIds",
        "documentVersion",
        "thinning",
        "onlyHeaders",
    ]
}


class Api:
    """
    FEWS PI-REST api it needs an server url and a logger.

    All variables related to PI-REST variables are defined camelCase. All others are
    snake_case.
    """

    def __init__(self, url, logger):
        self.document_format = "PI_JSON"
        self.url = url
        self.parameters = self._get_parameters()
        self.locations = None
        self.logger = logger

    def _get_parameters(self):
        rest_url = f"{self.url}parameters"
        parameters = dict(documentFormat=self.document_format)
        response = requests.get(rest_url, parameters)

        if response.status_code == 200:
            if "timeSeriesParameters" in response.json().keys():
                par_df = pd.DataFrame(response.json()["timeSeriesParameters"])
                par_df.set_index("id", inplace=True)
                return par_df
            else:
                return None

    def get_filters(self, filterId=None):
        """Get filters as dictionary, or sub-filters if a filterId is specified."""
        rest_url = f"{self.url}filters"

        parameters = {"documentFormat": self.document_format, "filterId": filterId}

        response = requests.get(rest_url, parameters)

        if response.status_code == 200:
            if "filters" in response.json().keys():
                filters = {
                    item["id"]: {
                        key: value for key, value in item.items() if not key == "id"
                    }
                    for item in response.json()["filters"]
                }
                return filters
            else:
                self.logger.warning('no filter returned')
                return None

    def get_parameters(self, filterId, locationIds=None):
        """Get parameters. FilterId is required. A list of locations optional."""
        result = None

        timeseries = self.get_timeseries(
            filterId=filterId,
            locationIds=locationIds,
            parameterIds=self.parameters.index.to_list(),
            onlyHeaders=True,
        )

        if "timeSeries" in timeseries.keys():
            result = list(
                set(
                    [
                        series["header"]["parameterId"]
                        for series in timeseries["timeSeries"]
                    ]
                )
            )

        else:
            self.logger.warning(
                f"no timeSeries in filter {filterId} for locations {locationIds}"
            )

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

        response = requests.get(rest_url, parameters)
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

        return gdf

    def get_timeseries(
        self,
        filterId,
        locationIds=None,
        startTime=None,
        endTime=None,
        parameterIds=None,
        documentVersion=None,
        thinning=None,
        onlyHeaders=False,
        unreliables=False,
    ):
        """Get timeseries within a filter, optionally filtered by other variables."""
        start = pd.Timestamp.now()
        result = None
        rest_url = f"{self.url}timeseries"

        parameters = {
            key: value
            for key, value in locals().items()
            if value and (key in _REQUEST_PARAMETERS_ALLOWED["timeseries"])
        }

        parameters.update({"documentFormat": self.document_format})

        response = requests.get(rest_url, parameters)

        if response.status_code == 200:
            if onlyHeaders:
                delta = pd.Timestamp.now() - start
                delta = delta.seconds + delta.microseconds / 1000000
                self.logger.info(f"get timeseries headers in {delta} seconds")
                return response.json()

            elif "timeSeries" in response.json().keys():
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

                delta = pd.Timestamp.now() - start
                delta = delta.seconds + delta.microseconds / 1000000
                self.logger.info(f"get timeseries in {delta} seconds")

                return response.json()["timeZone"], result

            else:
                self.logger.info("returning emtpy timeseries")
                return response.json()

        else:
            self.logger.error(
                f"server responded with error ({response.status_code}): {response.text}"
                f"url send to the server was: {response.url}"
            )

        if result is None:
            self.logger.warning("method returns None")

        return result
