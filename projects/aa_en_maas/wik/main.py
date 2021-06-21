"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from config import TITLE, LOG_LEVEL, LOG_FILE, TILE_SOURCES

from server_config import BUFFER

from fewsbokeh import map_figure, time_figure
import logging
from logging.handlers import RotatingFileHandler
from bokeh import events
from bokeh.io import curdoc
from bokeh.models.widgets import (
    Div,
    Button,
    Select,
    MultiSelect,
    Panel,
    Tabs,
    DatePicker,
    DateRangeSlider,
)
from bokeh.models import ColumnDataSource, Range1d, RadioGroup, CheckboxGroup, Div, Legend, TapTool
from bokeh.layouts import row, column
import ctypes
import numpy as np
import os
from copy import copy, deepcopy

from datamodel import Data
import pandas as pd

USE_JINJA_TEMPLATE = False
_UNITS_MAPPING = dict(nonequidistant="noneq", second="sec")


def _screen_resolution():
    """Compute server screen resolution."""
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))

    return width, height


def _remove_timefig():
    index = True

    while index:
        index = next(
            (idx for idx, tab in enumerate(tabs.tabs) if tab.name == "grafiek"), None
        )
        if index:
            tabs.tabs.remove(tabs.tabs[index])


def _activate_timefig():
    index = next(
        (idx for idx, tab in enumerate(tabs.tabs) if tab.name == "grafiek"), None
    )

    tabs.active = index


def _datetime_offset(values, offset_years):
    offset_sign = np.sign(offset_years)
    return tuple(
        pd.Timestamp(val * 1000000)
        + offset_sign * pd.DateOffset(years=abs(offset_years))
        for val in values
    )


def _clean_filters():
    # clean parameters filter
    options = [i for i in data.parameters.options if i[0] in data.parameters.ids]
    select_parameters.options = options

    parameters_select = [
        val for val in select_parameters.value if val in data.parameters.ids
    ]

    select_parameters.value = parameters_select


def _create_time_col(time_figs):
    for fig in time_figs:
        fig.height = int(height * 0.78 * 0.75 / len(time_figs))
        fig.width = int(width * 0.75)

    time_col = column(time_figs)
    time_col.children.append(search_fig)
    time_col.children.append(row(Div(width=40, text=""), period_slider))

    return time_col


def _create_timefig():
    """Create a time-fig."""
    if all([select_locations.value, select_parameters.value]):
        print(select_locations.value, select_parameters.value)
        location_ids = list(select_locations.value)
        parameter_ids = list(select_parameters.value)
        # print(select_parameters.value)
        data.create_timeseries(location_ids, parameter_ids)

        logger.debug("event: _create_time_fig")
        # print(data.timeseries.timeseries)
        # update timeseries search select
        if not data.timeseries.timeseries.empty:

            # difine top-figs
            top_figs = []
            glyphs = data.timeseries.hr_glyphs
            for idx, (key, values) in enumerate(glyphs.items()):
                if idx == 0:
                    fig_title = ",".join(select_locations.value)
                else:
                    fig_title = ""

                if idx == len(glyphs.items()) - 1:
                    x_axis_visible = True
                else:
                    x_axis_visible = False

                if len(select_parameters.value) == 1:
                    y_axis_label = select_parameters.value[0]
                else:
                    fews_parameters = data.fews_api.parameters
                    unit = fews_parameters.loc[
                        fews_parameters["parameterGroup"] == key
                    ]["displayUnit"].to_list()[0]
                    y_axis_label = f"{key} [{unit}]"

                graph = data.timeseries.hr_graphs[key]
                top_figs += [
                    time_figure.generate(
                        title=fig_title,
                        sizing_mode="stretch_both",
                        x_axis_label="",
                        y_axis_label=y_axis_label,
                        x_axis_visible=x_axis_visible,
                        x_range=time_figs_x_range,
                        y_range=graph["y_range"],
                        glyphs=values,
                    )
                ]

            # update search-data
            ts_labels = data.timeseries.timeseries["label"].to_list()
          
            select_search_timeseries.options = ts_labels
            print("1",select_search_timeseries.options)
            select_search_timeseries.value = ts_labels[0]
            print("2",select_search_timeseries.value)

            # update layout
            search_fig.yaxis[0].ticker = [
                data.timeseries.lr_y_range.start,
                data.timeseries.lr_y_range.end,
            ]

            search_fig.ygrid[0].ticker = [
                data.timeseries.lr_y_range.start,
                data.timeseries.lr_y_range.end,
            ]
            ts_labels = data.timeseries.timeseries["label"].to_list()
            print ("3",ts_labels)
            time_col = _create_time_col(top_figs)
            _remove_timefig()
            tabs.tabs.append(Panel(child=time_col, title="grafiek", name="grafiek"))


def update_on_double_tap(event):
    """Reset selected locarions on double tab."""
    logger.debug("event: update_on_double_tap")

    data.locations._update_selected([])
    select_locations.value = []


def update_on_tap(event):
    """Update when tap in map with location selected."""
    logger.debug("event: update_on_tap")
    #x, y = event.__dict__["x"], event.__dict__["y"]

    # update datamodel (locations selected)
    #distance_threshold = (map_fig.x_range.end - map_fig.x_range.start) * 0.005
    #location_ids = data.update_map_tab(x, y, distance_threshold)

    # update locations filter
    src = data.locations.source
    mask = np.isin(src.data["index"], src.selected.indices)
    location_ids = list(np.array(src.data["locationId"])[mask])
    select_locations.value = location_ids


def update_on_filter_select(attrname, old, new):
    """Update when user selects toggles filters."""
    logger.debug("event: update_on_filter_select")

    values = [item.value for item in filters]
    values = [item for sublist in values for item in sublist]
    # update subfilters with selected filters
    data.update_filter_select(values)

    # set locations options

    select_locations.options = data.locations.options
    # print(data.parameters.options)
    if len(select_locations.value) == 0:
        print(data.parameters.options)
        select_parameters.options = data.parameters.options

        # # clean filters
        _clean_filters()


def update_on_locations_select(attrname, old, new):
    """Update when user selects in locations filter."""
    logger.debug("event: update_on_locations_select")
    locations_select = list(select_locations.value)
    
    # update datamodel (locations & parameters)
    data.update_locations_select(locations_select)
    
    # update selected ids
    src = data.locations.source
    mask = np.isin(src.data["locationId"], locations_select)
    src.selected.indices = list(np.array(src.data["index"])[mask])

    # clean filters
    _clean_filters()

    # update timefig (if locs, pars are selected)
    _create_timefig()


def update_on_parameters_select(attrname, old, new):
    """Update when user selects in parameter filter."""
    logger.debug("event: update_on_parameters_select")
  #  parameters_select = list(select_parameters.value)
    # clean filters
    _clean_filters()

    # update timefig (if locs, pars,are selected)
    _create_timefig()


def update_on_search_select(attrname, old, new):
    """Update low lr graph when user updates any selection."""
    logger.debug("event: update_on_search_select")
    start_datetime = pd.Timestamp(search_start_date_picker.value)
    end_datetime = pd.Timestamp(search_end_date_picker.value)
    search_series = select_search_timeseries.value
    if search_series:
        data.update_lr_timeseries(search_series, start_datetime, end_datetime)


def follow_period_interval(attrname, old, new):
    """Update low lr graph when user updates any selection."""
    # logger.debug("event: update_on_search_period")
    start_datetime = pd.Timestamp(new[0] * 1000000)
    end_datetime = pd.Timestamp(new[1] * 1000000)
    days = (end_datetime - start_datetime).days
    if days > 150:
        if old[0] != new[0]:
            # starttime is shifting
            period_slider.value = (
                start_datetime,
                start_datetime + pd.Timedelta(days=150),
            )
        else:
            period_slider.value = (end_datetime - pd.Timedelta(days=150), end_datetime)


def _update_patch(start_datetime, end_datetime):
    patch_src.data.update(
        {
            "x": [start_datetime, start_datetime, end_datetime, end_datetime],
            "y": [
                search_fig.y_range.start,
                search_fig.y_range.end,
                search_fig.y_range.end,
                search_fig.y_range.start,
            ],
        }
    )


def update_on_period(attrname, old, new):
    """Update triggered by date_range_sider."""
    # logger.debug("event: update_on_period")
    start_datetime, end_datetime = period_slider.value_as_datetime

    days = (end_datetime - start_datetime).days
    if days > 90:
        if old[0] != new[0]:
            # starttime is shifting
            period_slider.value = (
                start_datetime,
                start_datetime + pd.Timedelta(days=90),
            )
        else:
            period_slider.value = (end_datetime - pd.Timedelta(days=90), end_datetime)

    _update_patch(period_slider.value[0], period_slider.value[1])


def update_on_x_range(attrname, old, new):
    """Update when x_range start is updated."""
    logger.debug("event: update_on_changed_x_range")
    # convert all to pandas timestamps
    if not isinstance(time_figs_x_range.start, pd.Timestamp):
        start_datetime = pd.Timestamp(time_figs_x_range.start * 10 ** 6)
    else:
        start_datetime = time_figs_x_range.start
    if not isinstance(time_figs_x_range.end, pd.Timestamp):
        end_datetime = pd.Timestamp(time_figs_x_range.end * 10 ** 6)
    else:
        end_datetime = time_figs_x_range.end

    # determine condition for refinement
    fig_timedelta = end_datetime - start_datetime
    ts_timedelta = data.timeseries.end_datetime - data.timeseries.start_datetime

    # determine refinement or expansion
    if (
        (ts_timedelta / max(fig_timedelta, pd.Timedelta(hours=1)) > 2)
        | (start_datetime < (data.timeseries.start_datetime - ts_timedelta * BUFFER))
        | (end_datetime > (data.timeseries.end_datetime + ts_timedelta * BUFFER))
    ):
        data.update_hr_timeseries(start_datetime, end_datetime)

    # update fig-bounds
    centre_datetime = start_datetime + (end_datetime - start_datetime) / 2
    time_figs_x_range.bounds = (
        centre_datetime - pd.Timedelta(days=45),
        centre_datetime + pd.Timedelta(days=45),
    )

    # update patch_data
    _update_patch(start_datetime, end_datetime)

    # update period-slider value
    period_slider.value = (start_datetime, end_datetime)


def update_on_period_select(attrname, old, new):
    """Update triggered by date_range_sider throttled."""
    logger.debug("event: update_on_period_select")
    start_datetime, end_datetime = period_slider.value_as_datetime
    data.update_hr_timeseries(start_datetime, end_datetime)
    time_figs_x_range.reset_start = start_datetime
    time_figs_x_range.reset_end = end_datetime


def update_search_range(attrname, old, new):
    """Update search range by event."""
    logger.debug("event: update_search_range")
    start_datetime = pd.Timestamp(search_start_date_picker.value)
    end_datetime = pd.Timestamp(search_end_date_picker.value)
    search_range.start = start_datetime
    search_range.end = end_datetime
    period_slider.start = start_datetime
    period_slider.end = end_datetime


def update_search_fig():
    """Update low lr graph when user updates any selection."""
    logger.debug("event: update_search_fig")
    start_datetime = pd.Timestamp(search_start_date_picker.value)
    end_datetime = pd.Timestamp(search_end_date_picker.value)
    search_series = select_search_timeseries.value
    if search_series:
        data.update_lr_timeseries(search_series, start_datetime, end_datetime)

def update_background(attrname, old, new):
    """Update map_fig with new background."""
    tile_source = map_figure.get_tileource(background.labels[new])
    idx = next(idx for idx, i in enumerate(map_fig.renderers) if i.name == "background")
    map_fig.renderers[idx].tile_source = tile_source

def update_map_layers(attrname, old, new):
    """Update visible map-layers on change."""
    for idx, i in enumerate(map_layers.labels):
        if idx in new:
            map_fig.renderers[map_fig_idx[i]].visible = True
        else:
            map_fig.renderers[map_fig_idx[i]].visible = False


log_dir = LOG_FILE.parent
log_dir.mkdir(exist_ok=True)
logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))
fh = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 10, backupCount=1)
fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(logFormatter)
logger.addHandler(fh)

# %% allow origin to server address
os.environ["BOKEH_ALLOW_WS_ORIGIN"] = "*"

# %% define the data object
data = Data(logger)

# %% define map figure widget and handlers
# ToDo: data.locations.source toevoegen
map_glyphs = [
    {
        "type": "circle",
        "size": 10,
        "source": data.locations.source,
        "line_color": "line_color",
        "fill_color": "fill_color",
        "selection_color":"red",
        "nonselection_fill_alpha":1,
        "nonselection_line_alpha":1,
        "hover_color": "red",
        "hover_alpha": 0.6,
        "line_width": 1,
        "legend_field": "label",
    }
]

map_fig = map_figure.generate(
    bounds=data.locations.bounds,
    glyphs=map_glyphs,
    background="topografie",
    map_layers=TILE_SOURCES
)

map_fig.name = "map_fig"

# event to select locations on the map
map_fig.on_event(events.Tap, update_on_tap)



# event to deselect all selected locations
#map_fig.on_event(events.DoubleTap, update_on_double_tap)

# %% define map-controls and handlers
map_options = list(TILE_SOURCES.keys())
map_active = [idx for idx, v in enumerate(TILE_SOURCES.values()) if v["visible"]]
map_layers = CheckboxGroup(labels=map_options, active=map_active)

map_fig_idx = {
    i.name: idx for idx, i in enumerate(map_fig.renderers) if i.name in map_layers.labels
    }

map_layers.on_change("active", update_map_layers)

background = RadioGroup(labels=["topografie", "luchtfoto"], active=0)

background.on_change("active", update_background)

map_controls = column(Div(text="<b>Kaartopties</b><br><br>Kaartlagen"),
                      map_layers,
                      Div(text="Achtergrond"),
                      background)

# %% define main filter selection and handlers
filters = list()
for name, subfilter in zip(data.filters.names, data.filters.filters):
    select_filter = MultiSelect(
        title=f"{name}:",
        value=subfilter.value,
        options=subfilter.options,
    )
    select_filter.size = min(len(subfilter.options), 7)
    select_filter.on_change("value", update_on_filter_select)
    filters += [select_filter]

# %% define location selection and handlers
select_locations = MultiSelect(
    title="Locaties:", value=[], options=data.locations.options
)

select_locations.on_change("value", update_on_locations_select)
# select_locations.js_link("value",
#                          data.locations.source.selected,
#                          "indices")

# %% define parameter selection and handlers
select_parameters = MultiSelect(
    title="Parameters:", value=[], options=data.parameters.options
)

select_parameters.on_change("value", update_on_parameters_select)


search_start_date_picker = DatePicker(
    title="start datum",
    value=data.search_start_datetime.strftime("%Y-%m-%d"),
    min_date=data.first_value_datetime.strftime("%Y-%m-%d"),
    max_date=data.search_start_datetime.strftime("%Y-%m-%d"),
)

search_end_date_picker = DatePicker(
    title="eind datum",
    value=data.now.strftime("%Y-%m-%d"),
    min_date=data.search_start_datetime.strftime("%Y-%m-%d"),
    max_date=data.now.strftime("%Y-%m-%d"),
)


search_start_date_picker.on_change("value", update_search_range)
search_end_date_picker.on_change("value", update_search_range)

search_button = Button(label="update zoekgrafiek", button_type="success")
search_button.on_click(update_search_fig)


select_search_timeseries = Select(title="Zoektijdserie:", value=None, options=[])
select_search_timeseries.on_change("value", update_on_search_select)

# %% define empty time_figs and fig-handlers
centre_datetime = (
    data.timeseries.start_datetime
    + (data.timeseries.end_datetime - data.timeseries.start_datetime) / 2
)

time_figs_x_range = Range1d(
    start=data.timeseries.start_datetime,
    end=data.timeseries.end_datetime,
    bounds=(
        centre_datetime - pd.Timedelta(days=45),
        centre_datetime + pd.Timedelta(days=45),
    )
)

time_figs_x_range.on_change("end", update_on_x_range)
time_figs_x_range.on_change("start", update_on_x_range)

print(time_figs_x_range.id)

time_figs_y_range = Range1d(start=-1, end=1, bounds=None)

time_figs = [
    time_figure.generate(
        title="selecteer locatie en paramameter",
        y_axis_label="-",
        x_range=time_figs_x_range,
        y_range=time_figs_y_range,
    )
]

search_range = Range1d(
    start=pd.Timestamp(search_start_date_picker.value),
    end=pd.Timestamp(search_end_date_picker.value),
    bounds="auto",
)

search_fig = time_figure.generate(
    x_axis_label=data.timeseries.x_axis_label,
    y_axis_label="",
    x_axis_visible=True,
    x_range=search_range,
    y_range=data.timeseries.lr_y_range,
    show_toolbar=False,
    glyphs=[data.timeseries.lr_glyph],
)

search_fig.toolbar_location = None
search_fig.ygrid.visible = False
search_fig.yaxis[0].ticker = [
    data.timeseries.lr_y_range.start,
    data.timeseries.lr_y_range.end,
]

search_fig.ygrid[0].ticker = [
    data.timeseries.lr_y_range.start,
    data.timeseries.lr_y_range.end,
]

patch_src = ColumnDataSource(
    {
        "x": [
            data.timeseries.start_datetime,
            data.timeseries.start_datetime,
            data.timeseries.end_datetime,
            data.timeseries.end_datetime,
        ],
        "y": [
            search_fig.y_range.start,
            search_fig.y_range.end,
            search_fig.y_range.end,
            search_fig.y_range.start,
        ],
    }
)

search_fig.patch(x="x", y="y", source=patch_src, alpha=0.5, line_width=2)

period_slider = DateRangeSlider(
    value=(data.timeseries.start_datetime, data.timeseries.end_datetime),
    start=data.timeseries.search_start_datetime,
    end=data.timeseries.search_end_datetime,
)
period_slider.format = "%d-%m-%Y"

period_slider.on_change("value", update_on_period)
period_slider.js_link("value_throttled", time_figs_x_range, "start", attr_selector=0)
period_slider.js_link("value_throttled", time_figs_x_range, "end", attr_selector=1)

# %% define layout
width = 1920 * 0.82
height = 1080 * 0.82


select_locations.size = 10
#map_fig.sizing_mode = "stretch_width"
map_fig.height = int(height * 0.75)
map_fig.width = int(width * 0.65)
map_controls.sizing_mode = "stretch_both"
map_panel = Panel(child=row(map_fig,map_controls),
                  title="kaart",
                  name="kaart")
search_fig.width = int(width * 0.75)
search_fig.height = int(height * 0.15 * 0.75)
#period_slider.width = int(width * 0.75 - 80)
period_slider.width = int(width * 0.75)
period_slider.align = "end"

time_col = _create_time_col(time_figs)

time_panel = Panel(child=time_col, title="grafiek", name="grafiek")
tabs = Tabs(tabs=[map_panel, time_panel], name="tabs")

search_start_date_picker.sizing_mode = "stretch_both"
search_end_date_picker.sizing_mode = "stretch_both"
search_button.sizing_mode = "stretch_width"
search_period_control = column(
    row(search_start_date_picker, search_end_date_picker), search_button
)

search_period_control.width = int(width * 0.2)

controls = column(filters + [select_locations,
                             select_parameters,
                             search_period_control,
                             select_search_timeseries]
                  )
# controls.height = int(height * 0.75 - 80)
layout = row(controls, tabs)

curdoc().add_root(layout)
curdoc().title = TITLE
