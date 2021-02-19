"""Datamodel for Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from server_config import URL, NOW, SSL_VERIFY

from config import (
    MAP_BUFFER,
    FILTER_PARENT,
    EXCLUDE_PARS,
    SEARCH_YEARS,
    FILTER_MONTHS,
    TIMESERIES_DAYS
)

from itertools import cycle
import pandas as pd
import geopandas as gpd
import numpy as np
import math
from bokeh.models import ColumnDataSource, Range1d
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
        self.now = NOW
        self.start_datetime = self.now - pd.DateOffset(
            days=TIMESERIES_DAYS)
        self.first_value_datetime = self.now - pd.DateOffset(
            years=SEARCH_YEARS)
        self.search_start_datetime = self.now - pd.DateOffset(
            months=FILTER_MONTHS)
        self.fews_api = fews_rest.Api(URL, logger, filterId, SSL_VERIFY)
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
                                          self.now,
                                          self.start_datetime,
                                          self.search_start_datetime)
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
        self.locations.fetch(filter_id)
        self.parameters.fetch(
            self.fews_api._get_parameters(filterId=filter_id))

    def update_locations_select(self, location_names):
        """Update datamodel on selected locations."""
        location_ids = self.locations._to_ids(location_names)
        self.locations._update_selected(location_ids)

        if location_ids:
            location_ids = self.include_child_locations(location_ids)
            headers = self.fews_api.get_headers(
                filterId=self.filters.selected['id'],
                endTime=self.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                parameterIds=self.parameters.df.index.to_list(),
                locationIds=location_ids)
            if headers is not None:
                self.timeseries.headers = headers
                self.parameters.update(
                    list(set([item['parameterId'] for item in headers])))

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

    def create_timeseries(self, location_names, parameter_names):
        """Update timeseries."""

        # some variables for later use
        self.timeseries.title = ",".join(location_names)

        # get parameter and location ids
        location_ids = self.locations._to_ids(location_names)
        location_ids = self.include_child_locations(location_ids)
        parameter_ids = self.fews_api.to_parameter_ids(parameter_names)

        parameter_groups = self.fews_api.parameters.loc[
            parameter_ids]["parameterGroup"].to_list()

        self.timeseries.create(location_ids,
                               parameter_ids,
                               self.filters.selected['id'],
                               parameter_groups)

    def update_lr_timeseries(self, search_series, start_datetime, end_datetime):
        """Update lr timeseries."""
        self.timeseries.search_start_datetime = start_datetime
        self.timeseries.search_end_datetime = end_datetime
        # self.timeseries.end_datetime = end_datetime
        # self.timeseries.start_datetime = end_datetime - pd.DateOffset(
        #     days=TIMESERIES_DAYS)
        df = self.timeseries.timeseries
        location_id = df.loc[df['label'] == search_series, 'location_id'].to_list()[0]
        parameter_id = df.loc[df['label'] == search_series, 'parameter_id'].to_list()[0]
        result = self.timeseries.get_lr_data(self.filters.selected['id'],
                                             location_id,
                                             parameter_id,
                                             start_datetime=start_datetime,
                                             end_datetime=end_datetime)

        if result is not None:
            ts = next((ts for ts in result[1] if not ts['events'].empty), None)

        if ts is not None:
            self.timeseries.lr_data = ts["events"]

        source = ColumnDataSource(self.timeseries.lr_data)
        self.timeseries.lr_glyph['source'].data.update(source.data)

        y_start = math.floor(min(source.data["value"]) * 10) / 10
        y_end = math.ceil(max(source.data["value"]) * 10) / 10
        self.timeseries.lr_y_range.start = y_start
        self.timeseries.lr_y_range.end = y_end
        # print(y_start, y_end)

    def update_hr_timeseries(self, start_datetime, end_datetime):
        """Update hr timeseries."""
        df = self.timeseries.timeseries
        location_ids = list(df['location_id'].unique())
        parameter_ids = list(df['parameter_id'].unique())

        self.timeseries.start_datetime = start_datetime
        self.timeseries.end_datetime = end_datetime
        timespan = (end_datetime - start_datetime).days
        thinner = int(timespan * 86400 * 1000 / width)
        _, hr_data = self.fews_api.get_timeseries(
            filterId=self.filters.selected['id'],
            locationIds=location_ids,
            parameterIds=parameter_ids,
            qualifierIds=[" "],
            startTime=start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            endTime=end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            thinning=thinner)

        # update data sources
        for ts in hr_data:
            if "events" in ts.keys():
                if not ts["events"].empty:
                    header = ts["header"]
                    parameter_id = header["parameterId"]
                    location_id = header["locationId"]
                    df.loc[(location_id, parameter_id), "source"].data.update(
                        ColumnDataSource(ts["events"]).data)

        # update graph y-ranges
        for key, value in self.timeseries.hr_graphs.items():
            y_range = value["y_range"]
            glyphs = self.timeseries.hr_glyphs[key]
            y_end = max([glyph["source"].data["value"].max() for glyph in glyphs])
            y_start = min([glyph["source"].data["value"].min() for glyph in glyphs])
            y_range.end = y_end
            y_range.start = y_start
            y_range.reset_end = y_end
            y_range.reset_start = y_start

    def get_search_timeseries(self):
        """Update options and values for search timeseries."""
        options = [f"{ts['location_name']} ,[{ts['parameter_name']}]"
                   for ts in self.timeseries.search_timeseries]

        parameter_value = self.fews_api.to_parameter_names([
            self.timeseries.search_value['parameter']])[0]

        location_value = self.locations.df.loc[
            self.locations.df['locationId'] == self.timeseries.search_value[
                'location']]['shortName'].to_list()[0]

        value = f"{location_value} ,[{parameter_value}]"
        return options, value

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

            self.fetch(filterId)

        def fetch(self, filterId):
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

            self.df = df.sort_values("shortName")
            self.df.reset_index(drop=True, inplace=True)

            self.names = self.df['shortName'].to_list()
            self.ids = self.df['locationId'].to_list()

            self.pluvial.data.update(ColumnDataSource("x",
                                                      "y",
                                                      data=self.df.loc[self.df["type"]
                                                                       == "neerslag"]
                                                      ).data)

            self.other.data.update(ColumnDataSource("x",
                                                    "y",
                                                    data=self.df.loc[self.df["type"]
                                                                     == "overig"]
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
            self.df = None
            self.names = None
            self.search_parameter = None
            self.exclude = exclude
            self.fetch(fews_api._get_parameters(filterId))

        def fetch(self, df):
            """Fetch new parameters filterId."""
            self.df = df.loc[~df.index.isin(self.exclude)].sort_values("name")
            self.ids = self.df.index.to_list()
            self.names = self.df['name'].to_list()
            self.groups = self.df['parameterGroup'].to_list()

        def update(self, parameter_ids):
            """Update ids and names selected."""
            parameter_ids = [par for par in parameter_ids if par not in self.exclude]
            df = self.df.loc[parameter_ids].sort_values("name")
            self.ids = df.index.to_list()
            self.names = df["name"].to_list()
            self.groups = df["parameterGroup"].to_list()

    class TimeSeries(object):
        """TimeSeries data."""

        def __init__(self,
                     fews_api,
                     logger,
                     now,
                     start_datetime,
                     search_start_datetime):
            self.hr_data = None
            self.lr_data = None
            self.fews_api = fews_api
            self.logger = logger
            self.start_datetime = start_datetime
            self.end_datetime = now
            self.search_end_datetime = now
            self.search_start_datetime = search_start_datetime
            self.time_zone = None
            self.timeseries = None
            self.search_value = None
            self.headers = None
            self.title = None
            self.hr_graphs = None
            self.x_bounds = None
            self.lr_y_range = Range1d(start=-0.1, end=0.1, bounds=None)
            self.hr_glyphs = None
            self.lr_glyph = None

        def get_lr_data(self,
                        filter_id,
                        location_id,
                        parameter_id,
                        start_datetime=None,
                        end_datetime=None):
            """Get the low resolution data in a pandas dataframe."""
            if start_datetime is not None:
                self.search_start_datetime = start_datetime
            if end_datetime is not None:
                self.search_end_datetime = end_datetime

            timespan = (self.search_end_datetime - self.search_start_datetime).days
            thinner = int(timespan * 86400 * 1000 / width)

            result = self.fews_api.get_timeseries(
                filterId=filter_id,
                locationIds=[location_id],
                parameterIds=[parameter_id],
                qualifierIds=[" "],
                startTime=self.search_start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                endTime=self.search_end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                thinning=thinner)

            return result

        def create(self,
                   location_ids,
                   parameter_ids,
                   filter_id,
                   parameter_groups):
            # print(location_ids, parameter_ids, filter_id, parameter_groups)
            """Update timeseries data."""
            # high resolution data
            timespan = (self.end_datetime - self.start_datetime).days
            thinner = int(timespan * 86400 * 1000 / width)
            self.time_zone, self.hr_data = self.fews_api.get_timeseries(
                filterId=filter_id,
                locationIds=location_ids,
                parameterIds=parameter_ids,
                qualifierIds=[" "],
                startTime=self.start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                endTime=self.end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                thinning=thinner)

            # initalize results
            self.hr_glyphs = {group: [] for group in parameter_groups}
            self.hr_graphs = {group: {
                "x_bounds": {'start': self.start_datetime, 'end': self.end_datetime},
                "y_bounds": {'start': [], 'end': []}}
                              for group in parameter_groups}

            timeseries = []
            colors = cycle(palette)
            # x_bounds = {'start': [], 'end': []}
            for ts in self.hr_data:
                if "events" in ts.keys():
                    if not ts["events"].empty:
                        header = ts["header"]
                        group = self.fews_api.parameters.loc[header["parameterId"]][
                            "parameterGroup"]
                        color = next(colors)
                        short_name = self.fews_api.locations.loc[header[
                            "locationId"]]["shortName"]
                        parameter_name = self.fews_api.parameters.loc[header[
                            "parameterId"]]["name"]
                        source = ColumnDataSource(ts["events"])
                        timeseries += [
                            {"location_id": header["locationId"],
                             "location_name": short_name,
                             "parameter_id": header["parameterId"],
                             "parameter_name": parameter_name,
                             "parameter_group": group,
                             "source": source}]
                        self.hr_glyphs[group] += [
                            {"type": "line",
                             "color": color,
                             "source": source,
                             "legend_label": f"{short_name} {parameter_name}"}
                                                ]
                        # x_bounds['start'] += [ts["events"]["datetime"].min()]
                        # x_bounds['end'] += [ts["events"]["datetime"].max()]
                        self.hr_graphs[group]['y_bounds']['start'] += [
                            ts["events"]["value"].min()]
                        self.hr_graphs[group]['y_bounds']['end'] += [
                            ts["events"]["value"].max()]

            self.timeseries = pd.DataFrame(timeseries)
            self.timeseries["label"] = self.timeseries.apply(
                (lambda x: f"{x['location_name']} ({x['parameter_name']})"),
                axis=1)
            self.timeseries.set_index(["location_id", "parameter_id"],
                                      inplace=True,
                                      drop=False)
            self.x_axis_label = "datum-tijd [gmt {0:+}]".format(
                int(float(self.time_zone)))

            # if len(x_bounds['start']) > 0:
            #     x_bounds['start'] = min(x_bounds['start'])
            # else:
            #     x_bounds['start'] = self.start_datetime

            # if len(x_bounds['end']) > 0:
            #     x_bounds['end'] = max(x_bounds['end'])
            # else:
            #     x_bounds['end'] = self.end_datetime

            # self.x_bounds = x_bounds
            for group in self.hr_glyphs.keys():
                if len(self.hr_graphs[group]['y_bounds']['start']) > 0:
                    self.hr_graphs[group]['y_bounds']['start'] = min(
                        self.hr_graphs[group]['y_bounds']['start'])
                else:
                    self.hr_graphs[group]['y_bounds']['start'] = 0

                if len(self.hr_graphs[group]['y_bounds']['end']) > 0:
                    self.hr_graphs[group]['y_bounds']['end'] = max(
                        self.hr_graphs[group]['y_bounds']['end'])
                else:
                    self.hr_graphs[group]['y_bounds']['end'] = 1
                if self.hr_graphs[group]['y_bounds'][
                        'end'] == self.hr_graphs[group]['y_bounds']['start']:
                    self.hr_graphs[group]['y_bounds']['end'] += 0.1
                    self.hr_graphs[group]['y_bounds']['start'] -= 0.1
                self.hr_graphs[group]['y_range'] = Range1d(
                    start=self.hr_graphs[group]['y_bounds']['start'],
                    end=self.hr_graphs[group]['y_bounds']['end'],
                    bounds=None)

            # low resolution data
            location_id = self.timeseries.iloc[0]['location_id']
            parameter_id = self.timeseries.iloc[0]['parameter_id']

            result = self.get_lr_data(filter_id,
                                      location_id,
                                      parameter_id)

            if result is not None:
                ts = next(
                    (ts for ts in result[1] if not ts[
                        'events'].empty), None)
            if ts is not None:
                self.lr_data = ts["events"]
                self.search_value = {"parameter": ts["header"]["parameterId"],
                                     "location": ts["header"]["locationId"]}

            source = ColumnDataSource(self.lr_data)
            colors = cycle(palette)
            self.lr_glyph = {"type": "line",
                             "color": next(colors),
                             "source": source}
            y_start = math.floor(min(source.data["value"]) * 10) / 10
            y_end = math.ceil(max(source.data["value"]) * 10) / 10
            self.lr_y_range.start = y_start
            self.lr_y_range.end = y_end
            # print(y_start, y_end)
