"""Datamodel for Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from server_config import FEWS_URL, NOW, SSL_VERIFY, BUFFER

from config import (
    BOUNDS,
    FILTER_PARENT,
    FILTER_API,
    EXCLUDE_PARS,
    SEARCH_YEARS,
    FILTER_MONTHS,
    TIMESERIES_DAYS,
    FILTER_RELATIONS,
    FILTER_COLORS
)

from itertools import cycle
import pandas as pd
import geopandas as gpd
import numpy as np
from bokeh.models import ColumnDataSource, Range1d
from fewsbokeh.sources import fews_rest
from fewsbokeh.time import Timer
from shapely.geometry import Point
from typing import List

from bokeh.palettes import Category10_10 as palette
import ctypes

_UNITS_MAPPING = dict(nonequidistant="noneq", second="sec")


def _screen_resolution():
    """Compute server screen resolution."""
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))

    return width, height


width, height = _screen_resolution()


def _flatten_relations(x, relations):
    return [i["relatedLocationId"] for i in x["relations"] if i["id"] in relations]

class Data(object):
    """Data-object with dataframes and update methods."""

    def __init__(self, logger):
        """Initialize data-class."""
        self.logger = logger
        self.timer = Timer(logger)
        self.now = NOW
        self.start_datetime = self.now - pd.DateOffset(days=TIMESERIES_DAYS)
        self.first_value_datetime = self.now - pd.DateOffset(years=SEARCH_YEARS)
        self.search_start_datetime = self.now - pd.DateOffset(months=FILTER_MONTHS)
        self.fews_api = fews_rest.Api(FEWS_URL, logger, FILTER_API, SSL_VERIFY)
        self.timer.report("FEWS-API initiated")
        self.filters = self.Filters(self.fews_api, logger)
        self.timer.report("filters initiated")
        self.locations = self.Locations(self.fews_api, logger)
        self.timer.report("locations initiated")
        self.parameters = self.Parameters(
            self.fews_api, logger, locationIds=[], exclude=EXCLUDE_PARS
        )
        self.timer.report("parameters initiated")
        self.timeseries = self.TimeSeries(
            self.fews_api,
            logger,
            self.now,
            self.start_datetime,
            self.search_start_datetime,
        )

        self.timer.reset("init finished")

    def include_child_locations(self, location_ids):
        """Expand a set of (parent) locations with children."""
        df = self.fews_api.locations
        location_ids += df[df["parentLocationId"].isin(location_ids)][
            "parentLocationId"
        ].index.to_list()
        
        return location_ids

    def update_filter_select(self, values):
        """Update datamodel on selected filter."""
        tuple_values = self.filters.get_tuples(values)
        self.locations.fetch(tuple_values)
        self.parameters.fetch(values)

    def update_locations_select(self, location_ids):
        """Update datamodel on selected locations."""
        self.locations._update_selected(location_ids)

        if location_ids:
            location_ids = self.include_child_locations(location_ids)
            headers = self.fews_api.get_headers(
                filterId=self.filters.selected["id"],
                endTime=self.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                parameterIds=self.parameters.df.index.to_list(),
                locationIds=location_ids,
            )
            print("headers=",headers)
            if headers is not None:
                self.timeseries.headers = headers
                self.parameters.update(
                    list(set([item["parameterId"] for item in headers]))
                )

    def update_map_tab(self, x, y, distance_threshold):
        """Update datamodel when map user tabs."""
        gdf = gpd.GeoDataFrame(self.locations.df)
        gdf["geometry"] = gdf.apply(lambda x: Point(x["x"], x["y"]), axis=1)
        gdf["distance"] = gdf["geometry"].distance(Point(x, y))
        gdf = gdf.loc[gdf["distance"] < distance_threshold]
        return list(
            set(gdf["locationId"].to_list() + self.locations.selected_ids)
        )

        #self.locations._update_selected(location_ids)

    def create_timeseries(self, location_ids, parameter_ids):
        """Update timeseries."""
        location_names = self.locations._to_names(location_ids)
        location_ids = self.include_child_locations(location_ids)
        self.timeseries.title = ",".join(location_names)

        parameter_groups = self.fews_api.parameters.loc[parameter_ids][
            "parameterGroup"
        ].to_list()

        self.timeseries.create(
            location_ids, parameter_ids, self.filters.selected["id"], parameter_groups
        )

    def update_lr_timeseries(self, search_series, start_datetime, end_datetime):
        """Update lr timeseries."""
        self.timeseries.search_start_datetime = start_datetime
        self.timeseries.search_end_datetime = end_datetime
        df = self.timeseries.timeseries
        location_id = df.loc[df["label"] == search_series, "location_id"].to_list()[0]
        parameter_id = df.loc[df["label"] == search_series, "parameter_id"].to_list()[0]
        result = self.timeseries.get_lr_data(
            self.filters.selected["id"],
            location_id,
            parameter_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )

        if result is not None:
            ts = next((ts for ts in result[1] if "events" in ts.keys()), None)

        if ts is not None:
            self.timeseries.lr_data = ts["events"]
        else:
            self.timeseries.lr_data = pd.DataFrame(data={"datetime": [], "value": []})

        source = ColumnDataSource(self.timeseries.lr_data)
        self.timeseries.lr_src.data.update(source.data)

        if not self.timeseries.lr_data.empty:
            y_start = (self.timeseries.lr_data["value"] * 10).apply(np.floor).min() / 10
            y_end = (self.timeseries.lr_data["value"] * 10).apply(np.ceil).max() / 10
        else:
            y_start, y_end = [-0.1, 0.1]

        if y_start == y_end:
            y_start -= 0.1
            y_end += 0.1
        self.timeseries.lr_y_range.start = y_start
        self.timeseries.lr_y_range.end = y_end

    def update_hr_timeseries(self, start_datetime, end_datetime):
        """Update hr timeseries."""
        df = self.timeseries.timeseries
        location_ids = list(df["location_id"].unique())
        parameter_ids = list(df["parameter_id"].unique())

        self.timeseries.start_datetime = start_datetime
        self.timeseries.end_datetime = end_datetime
        timespan = (end_datetime - start_datetime).days
        thinner = int(timespan * 86400 * 1000 / width)
        result = self.fews_api.get_timeseries(
            filterId=self.filters.selected["id"],
            locationIds=location_ids,
            parameterIds=parameter_ids,
            qualifierIds=[" "],
            startTime=start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            endTime=end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            thinning=thinner,
            buffer=BUFFER,
        )
        if result is not None:
            _, hr_data = result

        # update data sources
        for ts in hr_data:
            if "events" in ts.keys():
                if not ts["events"].empty:
                    header = ts["header"]
                    parameter_id = header["parameterId"]
                    location_id = header["locationId"]
                    df.loc[(location_id, parameter_id), "source"].data.update(
                        ColumnDataSource(ts["events"]).data
                    )

        # update graph y-ranges
        for key, value in self.timeseries.hr_graphs.items():
            y_range = value["y_range"]
            glyphs = self.timeseries.hr_glyphs[key]
            glyphs = [glyph for glyph in glyphs if len(glyph["source"].data["value"]) > 0]
            if glyphs:
                y_end = max([glyph["source"].data["value"].max() for glyph in glyphs])
                y_start = min([glyph["source"].data["value"].min() for glyph in glyphs])
      #          range_buffer = 0.1 * (y_end - y_start)
                range_buffer = 0.1 * max((y_end - y_start,1))
                y_range.end = y_end + range_buffer 
                y_range.start = y_start
                y_range.reset_end = y_end + range_buffer 
                y_range.reset_start = y_start

    def get_search_timeseries(self):
        """Update options and values for search timeseries."""
        options = [
            f"{ts['location_name']} ,[{ts['parameter_name']}]"
            for ts in self.timeseries.search_timeseries
        ]

        parameter_value = self.fews_api.to_parameter_names(
            [self.timeseries.search_value["parameter"]]
        )[0]

        location_value = self.locations.df.loc[
            self.locations.df["locationId"] == self.timeseries.search_value["location"]
        ]["shortName"].to_list()[0]

        value = f"{location_value} ,[{parameter_value}]"
        return options, value

    class Filters(object):
        """Available filters."""

        def __init__(self, fews_api, logger):
            """Initialize filters."""
            filters = fews_api.get_filters(filterId=FILTER_PARENT)[FILTER_PARENT][
                "child"
            ]
            self.names = [item["name"] for item in filters]
            self.filters = list()
            self.selected = {"id": FILTER_PARENT}

            # populate filters
            self.update(filters)

        class Subfilter(object):
            """Subfilter class for defining specs."""

            ident: str
            name: str
            options: List[tuple]
            value: list = []

        def update(self, filters):
            """Update subfilters."""
            for item in filters:
                if "child" in item.keys():
                    subfilter = self.Subfilter()
                    subfilter.ident = item["id"]
                    subfilter.name = item["name"]
                    subfilter.options = [(i["id"], i["name"]) for i in item["child"]]
                    self.filters += [subfilter]

        def get_tuples(self, filter_ids):
            """Return (id, name) tuples for filter_ids."""
            filter_options = [i.options for i in self.filters]
            filter_options = [i for sublist in filter_options for i in sublist]
            
            return [i for i in filter_options if i[0] in filter_ids]
     

    class Locations(object):
        """Available locations."""

        def __init__(self, fews_api, logger):
            """Initialize locations."""
            self.fews_api = fews_api
            self.logger = logger
            self.sets = {}
            self.bounds = BOUNDS
            self.df = None
            self.names = None
            self.ids = None
            self.options = []
            self.selected_ids = []
            self.selected_names = []

            self._init_df()

            self.source = ColumnDataSource(self.df)
            self.selected = ColumnDataSource("x", "y", data={"x": [], "y": []})

            # self.fetch(filterId)

        def _init_df(self):
            self.df = pd.DataFrame(
                columns=[
                    "x",
                    "y",
                    "locationId",
                    "shortName",
                    "parentLocationId",
                    "type",
                    "line_color",
                    "fill_color",
                    "label",
                ]
            )

        def fetch(self, values):
            """Fetch locations_set from filters (values)."""
            self.options = []
            self._init_df()

            for filter_id, filter_name in values:
                # if not yet collected, get locations
                if filter_id not in self.sets.keys():
                    self.sets[filter_id] = self.fews_api.get_locations(
                        filterId=filter_id,
                        includeLocationRelations=True
                        )
                    # filter related locations
                    if filter_id in FILTER_RELATIONS.keys():
                        relations = FILTER_RELATIONS[filter_id]
                        drop_idx = list(
                            set(
                                self.sets[filter_id].apply(
                                    _flatten_relations,
                                    args=(relations,),
                                    axis=1).explode().to_list()
                                )
                            )
                        self.sets[filter_id] = self.sets[filter_id].loc[
                            ~self.sets[filter_id]["locationId"].isin(drop_idx)
                            ]

                    # drop all unwanted columns
                    drop_cols = [
                        filter_id
                        for filter_id in self.sets[filter_id].columns
                        if filter_id not in self.df.columns
                    ]
                    self.sets[filter_id].drop(drop_cols, axis=1, inplace=True)
                    if filter_id in FILTER_COLORS.keys():
                        line_color = FILTER_COLORS[filter_id]["line"]
                        fill_color = FILTER_COLORS[filter_id]["fill"]
                    else:
                        line_color = "orange"
                        fill_color = "black"

                    self.sets[filter_id]["line_color"] = line_color
                    self.sets[filter_id]["nonselection_line_color"] = line_color
                    self.sets[filter_id]["fill_color"] = fill_color
                    self.sets[filter_id]["nonselection_fill_color"] = fill_color
                    self.sets[filter_id]["label"] = filter_name
                # add locations to df
                self.df = self.df.append(self.sets[filter_id])

            # sort dataframe remove duplicates and build options
            self.df = self.df.loc[self.df["parentLocationId"].isna()]
            self.df.sort_values(
                by="shortName", inplace=True, key=lambda x: x.str.lower()
            )
            self.df.drop_duplicates(subset=["locationId"], inplace=True)
            self.df.reset_index(drop=True, inplace=True)
            self.options = list(zip(self.df["locationId"], self.df["shortName"]))

            # fill columndatasource
            self.df["type"] = "overig"
            self.df.loc[
                self.df["locationId"].str.match("[A-Z]{3}-[A-Z]{3}-[A-Z]{3}"), "type"
            ] = "neerslag"
            cds = ColumnDataSource(self.df)

            self.source.data.update(cds.data)


        def _update_selected(self, location_ids):
            x = self.df.loc[self.df["locationId"].isin(location_ids)].x.to_list()
            y = self.df.loc[self.df["locationId"].isin(location_ids)].y.to_list()
            self.selected.data = {"x": x, "y": y}
            self.selected_ids = location_ids
            self.selected_names = self.df.loc[self.df["locationId"].isin(location_ids)][
                "shortName"
            ].to_list()

        def _to_ids(self, location_names):
            """Convert a list of location names to ids."""
            if isinstance(location_names, list):
                return self.fews_api.locations.loc[
                    self.fews_api.locations["shortName"].isin(location_names)
                ]["locationId"].to_list()
            else:
                return self.fews_api.locations.loc[
                    self.fews_api.locations["shortName"] == location_names
                ]["locationId"]

        def _to_names(self, location_ids):
            """Convert a list of location ids to names."""
            if isinstance(location_ids, list):
                return self.fews_api.locations.loc[
                    self.fews_api.locations["locationId"].isin(location_ids)
                ]["shortName"].to_list()
            else:
                return self.fews_api.locations.loc[
                    self.fews_api.locations["locationId"] == location_ids
                ]["shortName"]

    class Parameters(object):
        """Available parameters."""

        def __init__(self, fews_api, logger, locationIds, exclude=[]):
            """Initialize parameters."""
            self.fews_api = fews_api
            self.logger = logger
            self.groups = None
            self.sets = {}
            self.options = []
            self.ids = None
            self.df = None
            self.names = []
            self.search_parameter = None
            self.exclude = exclude

        def fetch(self, values):
            """Fetch new parameters filterId."""
            self.options = []
            self.df = pd.DataFrame(
                columns=[
                    "name",
                    "parameterType",
                    "unit",
                    "displayUnit",
                    "usesDatum",
                    "parameterGroup",
                ]
            )

            for item in values:
                # if not yet collected, get parameters
                if item not in self.sets.keys():
                    self.sets[item] = self.fews_api.get_parameters(filterId=item)
                    drop_cols = [
                        item
                        for item in self.sets[item].columns
                        if item not in self.df.columns
                    ]
                    self.sets[item].drop(drop_cols, axis=1, inplace=True)
                    self.sets[item] = self.sets[item][
                        ~self.sets[item].index.isin(EXCLUDE_PARS)
                    ]
                # add parameters from set to df
                self.df = self.df.append(self.sets[item])

            # sort dataframe remove duplicates and build options
            self.df.sort_values(by="name", inplace=True, key=lambda x: x.str.lower())
            self.df = self.df[~self.df.index.duplicated(keep="first")]
            self.options = list(zip(self.df.index, self.df["name"]))
            self.ids = self.df.index.to_list()
            self.names = self.df["name"].to_list()
            self.groups = self.df["parameterGroup"].to_list()

        def update(self, parameter_ids):
            """Update ids and names selected."""
            parameter_ids = [par for par in parameter_ids if par not in self.exclude]
            df = self.df.loc[parameter_ids].sort_values("name")
            self.ids = df.index.to_list()
            self.names = df["name"].to_list()
            self.groups = df["parameterGroup"].to_list()

    class TimeSeries(object):
        """TimeSeries data."""

        def __init__(
            self, fews_api, logger, now, start_datetime, search_start_datetime
        ):
            """Initialize timeseries."""
            self.hr_data = None
            self.lr_data = pd.DataFrame({"datetime": [], "value": []})
            self.lr_src = ColumnDataSource(self.lr_data)
            self.fews_api = fews_api
            self.logger = logger
            self.start_datetime = start_datetime
            self.end_datetime = now
            self.search_end_datetime = now
            self.search_start_datetime = search_start_datetime
            self.time_zone = None
            self.timeseries = None  # contains timeseries specs and source
            self.headers = None
            self.title = None
            self.hr_graphs = None
            self.x_bounds = None
            self.x_axis_label = "datum-tijd [gmt +1]"
            self.lr_y_range = Range1d(start=-0.1,
                                      end=0.1,
                                      min_interval=0.1,
                                      bounds=None)
            self.hr_glyphs = None
            self.lr_glyph = {"type": "line", "color": palette[0], "source": self.lr_src}

            self._init_timeseries()

        def _init_timeseries(self):
            self.timeseries = pd.DataFrame(
                columns=[
                    "location_id",
                    "location_name",
                    "parameter_id",
                    "parameter_name",
                    "parameter_group",
                    "source",
                    "label",
                ]
            )

        def get_lr_data(
            self,
            filter_id,
            location_id,
            parameter_id,
            start_datetime=None,
            end_datetime=None,
        ):
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
                thinning=thinner,
            )

            return result

        def create(self, location_ids, parameter_ids, filter_id, parameter_groups):
            """Update timeseries data."""
            # high resolution data
            self._init_timeseries()  # create an empty dataframe with ts specs
            timespan = (self.end_datetime - self.start_datetime).days
            thinner = int(timespan * 86400 * 1000 / width)
            result = self.fews_api.get_timeseries(
                filterId=filter_id,
                locationIds=location_ids,
                parameterIds=parameter_ids,
                qualifierIds=[" "],
                startTime=self.start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                endTime=self.end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                thinning=thinner,
                buffer=BUFFER,
            )
            print(result)

            if result is not None:
                self.time_zone, self.hr_data = result

                # initalize results
                self.hr_glyphs = {group: [] for group in parameter_groups}
                self.hr_graphs = {
                    group: {
                        "x_bounds": {
                            "start": self.start_datetime,
                            "end": self.end_datetime,
                        },
                        "y_bounds": {"start": [], "end": []},
                    }
                    for group in parameter_groups
                }

                timeseries = []
                colors = cycle(palette)
                # x_bounds = {'start': [], 'end': []}
                for ts in self.hr_data:
                    if "header" in ts.keys():
                        header = ts["header"]
                        group = self.fews_api.parameters.loc[header["parameterId"]][
                            "parameterGroup"
                        ]
                        color = next(colors)
                        short_name = self.fews_api.locations.loc[header["locationId"]][
                            "shortName"
                        ]
                        parameter_name = self.fews_api.parameters.loc[
                            header["parameterId"]
                        ]["name"]
                        ts_specs = {
                            "location_id": header["locationId"],
                            "location_name": short_name,
                            "parameter_id": header["parameterId"],
                            "parameter_name": parameter_name,
                            "parameter_group": group,
                        }
                    if "events" in ts.keys():
                        if not ts["events"].empty:
                            source = ColumnDataSource(ts["events"])
                            self.hr_graphs[group]["y_bounds"]["start"] += [
                                ts["events"]["value"].min()
                            ]
                            self.hr_graphs[group]["y_bounds"]["end"] += [
                                ts["events"]["value"].max()
                            ]
                    else:
                        source = ColumnDataSource({"datetime": [], "value": []})

                    ts_specs["source"] = source
                    timeseries += [ts_specs]
                    self.hr_glyphs[group] += [
                        {
                            "type": "line",
                            "color": color,
                            "source": source,
                            "legend_label": f"{short_name}",
               #             "legend_label": f"{short_name} {parameter_name}",
                        }
                    ]

                self.timeseries = pd.DataFrame(timeseries)
                if not self.timeseries.empty:
                    self.timeseries["label"] = self.timeseries.apply(
                        (lambda x: f"{x['location_name']} ({x['parameter_name']})"),
                        axis=1,
                    )
        
                    self.timeseries.set_index(
                        ["location_id", "parameter_id"], inplace=True, drop=False
                    )
                    self.x_axis_label = "datum-tijd [gmt {0:+}]".format(
                        int(float(self.time_zone))
                    )

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
                        if len(self.hr_graphs[group]["y_bounds"]["start"]) > 0:
                            self.hr_graphs[group]["y_bounds"]["start"] = min(
                                self.hr_graphs[group]["y_bounds"]["start"]
                            )
                        else:
                            self.hr_graphs[group]["y_bounds"]["start"] = 0

                        if len(self.hr_graphs[group]["y_bounds"]["end"]) > 0:
                            self.hr_graphs[group]["y_bounds"]["end"] = max(
                                self.hr_graphs[group]["y_bounds"]["end"]
                            )
                        else:
                            self.hr_graphs[group]["y_bounds"]["end"] = 1
                        if (
                            self.hr_graphs[group]["y_bounds"]["end"]
                            == self.hr_graphs[group]["y_bounds"]["start"]
                        ):
                            self.hr_graphs[group]["y_bounds"]["end"] -= 0.5
                            self.hr_graphs[group]["y_bounds"]["start"] += 0.5
                            
                        range_buffer = 0.1 * (
                            self.hr_graphs[group]["y_bounds"]["end"] - self.hr_graphs[group]["y_bounds"]["start"]
                            )
                        
                        self.hr_graphs[group]["y_range"] = Range1d(
                            start=self.hr_graphs[group]["y_bounds"]["start"],
                            end=self.hr_graphs[group]["y_bounds"]["end"] + range_buffer
                        )
