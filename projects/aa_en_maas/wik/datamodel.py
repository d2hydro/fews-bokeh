"""Datamodel for Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from config import (
    URL,
    MAP_BUFFER,
    FILTER_PARENT,
    EXCLUDE_PARS
)

from itertools import cycle
import pandas as pd
import geopandas as gpd
import numpy as np
from bokeh.models import ColumnDataSource
from fewsbokeh.sources import fews_rest
from fewsbokeh.time import Timer
from shapely.geometry import Point

from bokeh.palettes import Category10_10 as palette
import ctypes

_UNITS_MAPPING = dict(nonequidistant="noneq", second="sec")


def _screen_resolution():
    """Compute server screen resolution."""
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))

    return width, height


width, height = _screen_resolution()


class Data(object):
    """Data-object with dataframes and update methods."""

    def __init__(self, filterId, logger):
        self.logger = logger
        self.timer = Timer(logger)
        self.now = pd.Timestamp.now()
        self.end_datetime = self.now
        self.start_datetime = self.end_datetime - pd.DateOffset(years=1)
        self.fews_api = fews_rest.Api(URL, logger, filterId)
        self.timer.report("FEWS-API initiated")
        self.filters = self.Filters(filterId,
                                    self.fews_api,
                                    logger)
        self.timer.report("filters initiated")
        self.locations = self.Locations(filterId,
                                        self.fews_api,
                                        logger)
        self.timer.report("locations initiated")
        self.parameters = self.Parameters(filterId,
                                          self.fews_api,
                                          logger,
                                          locationIds=[],
                                          exclude=EXCLUDE_PARS)
        self.timer.report("parameters initiated")
        self.timeseries = self.TimeSeries(self.fews_api,
                                          logger,
                                          self.start_datetime,
                                          self.end_datetime)
        self.timer.reset("init finished")

    def include_child_locations(self, location_ids):
        """Expand a set of (parent) locations with children."""
        df = self.fews_api.locations
        location_ids += df[df["parentLocationId"].isin(location_ids)
                           ]["parentLocationId"].index.to_list()
        return location_ids

    def update_filter_select(self, filter_name):
        """Update datamodel on selected filter."""
        filter_id = next(item for item in self.filters.filters
                         if item['name'] == filter_name)['id']

        self.filters.update(filter_id)
        self.locations.update(filter_id)
        self.parameters.update(filter_id)

    def update_locations_select(self, location_names):
        """Update datamodel on selected locations."""
        location_ids = self.locations._to_ids(location_names)
        self.locations._update_selected(location_ids)

        if location_ids:
            location_ids = self.include_child_locations(location_ids)
            self.parameters.update(self.filters.selected['id'],
                                   locationIds=location_ids,
                                   start_datetime=self.start_datetime,
                                   end_datetime=self.start_datetime)

    def update_parameters_select(self, parameter_names):
        """Update datamodel on selected locations."""
        parameter_ids = self.fews_api.to_parameter_ids(parameter_names)

    def update_map_tab(self, x, y, distance_threshold):
        """Update datamodel when map user tabs."""
        gdf = gpd.GeoDataFrame(self.locations.df)
        gdf['geometry'] = gdf.apply(lambda x: Point(x['x'], x['y']), axis=1)
        gdf["distance"] = gdf["geometry"].distance(Point(x, y))
        gdf = gdf.loc[gdf["distance"] < distance_threshold]
        location_ids = list(set(gdf[
            "locationId"].to_list() + self.locations.selected_ids))

        self.locations._update_selected(location_ids)

    def update_search_dates(self, offset_years):
        """Update datamodel when offsets search-period."""
        offset_sign = np.sign(offset_years)
        self.start_datetime = self.start_datetime + offset_sign * pd.DateOffset(
            years=abs(offset_years))

        self.end_datetime = self.end_datetime + offset_sign * pd.DateOffset(
            years=abs(offset_years))

    def update_timeseries(self, location_names, parameter_names, qualifiers, timesteps):
        """Update timeseries."""
#        print(location_names, parameter_names, qualifiers, timesteps)
        self.logger.debug("bokeh: _update_time_fig")

        # some variables for later use
        self.timeseries.title = ",".join(location_names)

        # get parameter and location ids
        location_ids = self.locations._to_ids(location_names)
        location_ids = self.include_child_locations(location_ids)
        parameter_ids = self.fews_api.to_parameter_ids(parameter_names)
        qualifiers = [item.split(" ") for item in qualifiers]
        timesteps = [item.split(" ") for item in timesteps]

        self.timeseries.update(location_ids,
                               parameter_ids,
                               qualifiers,
                               timesteps,
                               self.filters.selected['id'],
                               self.parameters.groups)

    class Filters(object):
        """Available filters."""

        def __init__(self, filterId, fews_api, logger):
            self.filters = fews_api.get_filters(
                filterId=FILTER_PARENT)[FILTER_PARENT]["child"]

            self.ids = [item["id"] for item in self.filters]
            self.names = [item["name"] for item in self.filters]
            self.selected = dict()

            self.update(filterId)

        def update(self, filterId):
            """Update selected filter."""
            self.selected = next(item for item in self.filters
                                 if item['id'] == filterId)

    class Locations(object):
        """Available locations."""

        def __init__(self, filterId, fews_api, logger):
            self.fews_api = fews_api
            self.logger = logger
            self.bounds = None
            self.df = None
            self.names = None
            self.ids = None
            self.selected_ids = []
            self.selected_names = []
            self.pluvial = ColumnDataSource("x",
                                            "y",
                                            data={'x': [], 'y': []}
                                            )
            self.other = ColumnDataSource("x",
                                          "y",
                                          data={'x': [], 'y': []}
                                          )

            self.selected = ColumnDataSource("x",
                                             "y",
                                             data={'x': [], 'y': []}
                                             )

            self.update(filterId)

        def update(self, filterId):
            """Update locations by filterId."""
            gdf = self.fews_api.get_locations(filterId=filterId)
            self.bounds = gdf["geometry"].buffer(MAP_BUFFER).total_bounds

            df = pd.DataFrame(gdf.drop(["geometry"], axis=1))
            drop_cols = [col for col in df.columns if col not in ['x',
                                                                  'y',
                                                                  'locationId',
                                                                  'shortName',
                                                                  'parentLocationId',
                                                                  'type']]
            df.drop(drop_cols, axis=1, inplace=True)

            df = df.loc[df["parentLocationId"].isna()]
            df["type"] = "overig"
            df.loc[
                df["locationId"].str.match("[A-Z]{3}-[A-Z]{3}-[A-Z]{3}"), "type"
            ] = "neerslag"
            df.reset_index(drop=True, inplace=True)

            self.df = df

            self.names = df['shortName'].to_list()
            self.ids = df['locationId'].to_list()

            self.pluvial.data.update(ColumnDataSource("x",
                                                      "y",
                                                      data=df.loc[df["type"]
                                                                  == "neerslag"]
                                                      ).data)

            self.other.data.update(ColumnDataSource("x",
                                                    "y",
                                                    data=df.loc[df["type"] == "overig"]
                                                    ).data)

        def _update_selected(self, location_ids):
            x = self.df.loc[self.df['locationId'].isin(location_ids)].x.to_list()
            y = self.df.loc[self.df['locationId'].isin(location_ids)].y.to_list()
            self.selected.data = {"x": x, "y": y}
            self.selected_ids = location_ids
            self.selected_names = self.df.loc[self.df['locationId'].isin(
                location_ids)]['shortName'].to_list()

        def _to_ids(self, location_names):
            """Convert a list of location names to ids."""
            if isinstance(location_names, list):
                return self.fews_api.locations.loc[
                    self.fews_api.locations["shortName"].isin(location_names)][
                    "locationId"
                ].to_list()
            else:
                return self.fews_api.locations.loc[
                    self.fews_api.locations["shortName"] == location_names][
                    "locationId"
                ]

    class Parameters(object):
        """Available parameters."""

        def __init__(self, filterId, fews_api, logger, locationIds, exclude=[]):
            self.fews_api = fews_api
            self.logger = logger
            self.groups = None
            self.ids = None
            self.names = None
            self.timesteps = dict()
            self.qualifiers = dict()
            self.exclude = exclude
            self.update(filterId, locationIds=locationIds)

        def timestep_names(self, parameter_names=None):
            """Extract timestep names from timesteps."""
            timesteps = self.timesteps
            if parameter_names:
                parameter_ids = self.fews_api.to_parameter_ids(parameter_names)
                timesteps = {key: item for key, item in timesteps.items()
                             if key in parameter_ids}
            timesteps = [
                item for sublist in timesteps.values() for item in sublist]
            names = [" ".join(item.values()) for item in timesteps]
            return list(set(names))

        def qualifier_names(self, parameter_names=None):
            """Extract qualifier names from qualifiers."""
            qualifiers = self.qualifiers
            if parameter_names:
                parameter_ids = self.fews_api.to_parameter_ids(parameter_names)
                qualifiers = {key: item for key, item in qualifiers.items()
                              if key in parameter_ids}

            qualifiers = [item for sublist in qualifiers.values() for item in sublist]

            names = [" ".join(item) for item in qualifiers]
            return list(set(names))

        def update(self,
                   filterId,
                   start_datetime=None,
                   end_datetime=None,
                   locationIds=[]):
            """Update locations by filterId."""
            if locationIds:
                if start_datetime:
                    startTime = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
                    endTime = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
                self.ids, self.qualifiers, self.timesteps = self.fews_api.get_parameters(filterId=filterId,
                                                                                         startTime=startTime,
                                                                                         endTime=endTime,
                                                                                         locationIds=locationIds)

            else:
                self.ids = self.fews_api._get_parameters(
                    filterId=filterId).index.to_list()

            self.ids = [par for par in self.ids if par not in self.exclude]
            self.names = self.fews_api.to_parameter_names(self.ids)
            self.groups = self.fews_api.parameters.loc[
                self.ids]["parameterGroup"].to_list()

    class TimeSeries(object):
        """TimeSeries data."""

        def __init__(self, fews_api, logger, start_datetime, end_datetime):
            self.data = None
            self.fews_api = fews_api
            self.logger = logger
            self.start_datetime = start_datetime
            self.end_datetime = end_datetime
            self.time_zone = None
            self.time_series = None
            self.title = None
            self.graphs = None
            self.x_bounds = None
            self.glyphs = None

        def update(self,
                   location_ids,
                   parameter_ids,
                   qualifier_ids,
                   timesteps,
                   filter_id,
                   parameter_groups):
            """Update timeseries data."""
            print(location_ids, parameter_ids, qualifier_ids, timesteps, filter_id, parameter_groups)
            timespan = (self.start_datetime - self.start_datetime).days
            thinner = int(timespan * 86400 * 1000 / width)
            colors = cycle(palette)

            # get all timeseries from api
            self.time_zone, self.data = self.fews_api.get_timeseries(
                filterId=filter_id,
                locationIds=location_ids,
                qualifierIds=qualifier_ids,
                parameterIds=parameter_ids,
                startTime=self.start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                endTime=self.end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                thinning=thinner)
"""
            parameter_groups = self.fews_api.parameters.loc[
                parameter_ids]["parameterGroup"].to_list()

            self.glyphs = {group: [] for group in parameter_groups}
            self.graphs = {group: {"x_axis_visible": [],
                                   "x_bounds": {'start': [], 'end': []},
                                   "y_bounds": {'start': [], 'end': []}}
                           for group in parameter_groups}

            # assign a color-scheme
            color_df = pd.DataFrame(
                [
                    dict(
                        location=ts["header"]["locationId"],
                        parameter=ts["header"]["parameterId"],
                        ts_unit=ts["header"]["timeStep"]["unit"],
                        group=self.fews_api.parameters.loc[ts["header"]["parameterId"]][
                            "parameterGroup"
                        ],
                    )
                    for ts in self.data
                ]
                )
            color_df.sort_values(
                by=["group", "parameter", "ts_unit", "location"], inplace=True
            )
            color_df.set_index(["group", "location", "parameter", "ts_unit"],
                               inplace=True)
            color_df["color"] = None
            grouper = color_df.groupby("group")
            for _, df in grouper:
                for idx, row in df.iterrows():
                    color_df.loc[idx, "color"] = next(colors)

            x_bounds = {'start': [], 'end': []}
            for ts in self.data:
                if "events" in ts.keys():
                    header = ts["header"]
                    group = self.fews_api.parameters.loc[header["parameterId"]][
                        "parameterGroup"]
                    location = header["locationId"]
                    parameter = header["parameterId"]
                    ts_unit = header["timeStep"]["unit"]
                    color = color_df.loc[group, location, parameter, ts_unit]["color"]
                    short_name = self.fews_api.locations.loc[header[
                        "locationId"]]["shortName"]
                    parameter_name = self.fews_api.parameters.loc[header[
                        "parameterId"]]["name"]
                    unit_name = _UNITS_MAPPING[header["timeStep"]["unit"]]
                    self.glyphs[group] += [
                        {"type": "line",
                         "color": color,
                         "source": ColumnDataSource(ts["events"]),
                         "legend_label": f"{short_name} {parameter_name} [{unit_name}]"}
                                            ]
                    self.glyphs[group] += []
                    if not ts["events"].empty:
                        x_bounds['start'] += [ts["events"]["datetime"].min()]
                        x_bounds['end'] += [ts["events"]["datetime"].max()]
                        self.graphs[group]['y_bounds']['start'] += [ts["events"]
                                                                    ["value"].min()]
                        self.graphs[group]['y_bounds']['end'] += [ts["events"]
                                                                  ["value"].max()]

            self.x_axis_label = "datum-tijd [gmt {0:+}]".format(
                int(float(self.time_zone)))

            if len(x_bounds['start']) > 0:
                x_bounds['start'] = min(x_bounds['start'])
            else:
                x_bounds['start'] = self.start_datetime

            if len(x_bounds['end']) > 0:
                x_bounds['end'] = max(x_bounds['end'])
            else:
                x_bounds['end'] = self.end_datetime

            self.x_bounds = x_bounds
            for group in self.glyphs.keys():
                if len(self.graphs[group]['y_bounds']['start']) > 0:
                    self.graphs[group]['y_bounds']['start'] = min(self.graphs[group]
                                                                  ['y_bounds']['start'])
                else:
                    self.graphs[group]['y_bounds']['start']

                if len(self.graphs[group]['y_bounds']['end']) > 0:
                    self.graphs[group]['y_bounds']['end'] = max(self.graphs[group]
                                                                ['y_bounds']['end'])
                else:
                    self.graphs[group]['y_bounds']['end'] = 1
"""