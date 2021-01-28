"""Datamodel for Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from server_config import URL, NOW

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
        self.now = NOW
        self.end_datetime = self.now
        self.start_datetime = self.end_datetime - pd.DateOffset(
            days=TIMESERIES_DAYS)
        self.first_value_datetime = self.end_datetime - pd.DateOffset(
            years=SEARCH_YEARS)
        self.search_start_datetime = self.end_datetime - pd.DateOffset(
            months=FILTER_MONTHS)
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
                                          self.end_datetime,
                                          self.start_datetime,
                                          self.search_start_datetime,
                                          self.first_value_datetime)
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
                endTime=self.end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
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

    def update_search_dates(self, offset_years):
        """Update datamodel when offsets search-period."""
        offset_sign = np.sign(offset_years)
        self.first_value_datetime = self.first_value_datetime + offset_sign * pd.DateOffset(
            years=abs(offset_years))

        self.end_datetime = self.end_datetime + offset_sign * pd.DateOffset(
            years=abs(offset_years))

    def create_timeseries(self, location_names, parameter_names):
        """Update timeseries."""
#        print(location_names, parameter_names, qualifiers, timesteps)
        self.logger.debug("bokeh: _update_time_fig")

        # some variables for later use
        self.timeseries.title = ",".join(location_names)

        # get parameter and location ids
        location_ids = self.locations._to_ids(location_names)
        location_ids = self.include_child_locations(location_ids)
        parameter_ids = self.fews_api.to_parameter_ids(parameter_names)

        parameter_groups = self.fews_api.parameters.loc[
            parameter_ids]["parameterGroup"].to_list()

        search_parameter_id = self.fews_api.to_parameter_ids(
            [self.parameters.search_parameter])[0]

        self.timeseries.create(location_ids,
                               parameter_ids,
                               search_parameter_id,
                               self.filters.selected['id'],
                               parameter_groups)

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
                     end_datetime,
                     start_datetime,
                     search_start_datetime,
                     first_value_datetime):
            self.hr_data = None
            self.lr_data = None
            self.fews_api = fews_api
            self.logger = logger
            self.start_datetime = start_datetime
            self.end_datetime = end_datetime
            self.search_start_datetime = search_start_datetime
            self.first_value_datetime = first_value_datetime
            self.time_zone = None
            self.time_series = None
            self.headers = None
            self.title = None
            self.hr_graphs = None
            self.x_bounds = None
            self.hr_glyphs = None
            self.lr_glyph = None

        def timestep_names(self, parameter_names=None):
            """Extract timestep names from timesteps."""
            headers = self.headers
            if parameter_names:
                parameter_ids = self.fews_api.to_parameter_ids(parameter_names)
                headers = [item for item in headers
                           if item['parameterId'] in parameter_ids]

            names = []
            for header in headers:
                name = ""
                timestep = header['timeStep']
                if "multiplier" in timestep.keys():
                    name += f"{timestep['multiplier']} "
                name += timestep["unit"]

            names += [name]
            names = list(set(names))
            names.sort()
            return names

        def qualifier_names(self, parameter_names=None):
            """Extract qualifier names from qualifiers."""
            headers = self.headers
            if parameter_names:
                parameter_ids = self.fews_api.to_parameter_ids(parameter_names)
                headers = [item for item in headers
                           if item['parameterId'] in parameter_ids]

            names = []
            for item in headers:
                if 'qualifierId' in item.keys():
                    names += [" ".join(item['qualifierId'])]
                else:
                    names += [" "]
            names = list(set(names))
            names.sort()
            return names

        def create(self,
                   location_ids,
                   parameter_ids,
                   search_parameter_id,
                   filter_id,
                   parameter_groups):
            """Update timeseries data."""
            timespan = (self.end_datetime - self.search_start_datetime).days
            thinner = int(timespan * 86400 * 1000 / width)
            colors = cycle(palette)

            _, self.lr_data = self.fews_api.get_timeseries(
                filterId=filter_id,
                locationIds=location_ids,
                parameterIds=search_parameter_id,
                qualifierIds=[" "],
                startTime=self.search_start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                endTime=self.end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                thinning=thinner)
            # print(self.lr_data)
            # get the first timeseries with data, otherwise return empty
            df = next((ts['events'] for ts in self.lr_data if not ts[
                'events'].empty), {"datetime": [], "value": []})

            self.lr_glyph = {"type": "line",
                             "color": next(colors),
                             "source": ColumnDataSource(df)}

            # create high resolution glyphs
            # get all timeseries from api
            timespan = (self.end_datetime - self.start_datetime).days
            thinner = int(timespan * 86400 * 1000 / width)

            # download data
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

            colors = cycle(palette)
            x_bounds = {'start': [], 'end': []}
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
                        self.hr_glyphs[group] += [
                            {"type": "line",
                             "color": color,
                             "source": ColumnDataSource(ts["events"]),
                             "legend_label": f"{short_name} {parameter_name}"}
                                                ]
                        x_bounds['start'] += [ts["events"]["datetime"].min()]
                        x_bounds['end'] += [ts["events"]["datetime"].max()]
                        self.hr_graphs[group]['y_bounds']['start'] += [
                            ts["events"]["value"].min()]
                        self.hr_graphs[group]['y_bounds']['end'] += [
                            ts["events"]["value"].max()]

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
