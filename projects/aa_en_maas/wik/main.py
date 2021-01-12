"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""

from config import (
    TITLE,
    LOG_LEVEL,
    SERVER,
    FILTER_SELECTED,
)

from fewsbokeh import map_figure, time_figure
import logging

from bokeh import events
from bokeh.io import curdoc
from bokeh.models.widgets import Select, Panel, Tabs, MultiSelect
from bokeh.layouts import row, column
import ctypes
import os

from datamodel import Data

_UNITS_MAPPING = dict(nonequidistant="noneq", second="sec")


def _screen_resolution():
    """Compute server screen resolution."""
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))

    return width, height


def _remove_timefig():
    index = True

    while index:
        index = next((idx for idx, tab in enumerate(tabs.tabs)
                      if tab.name == 'grafiek'),
                     None)
        if index:
            tabs.tabs.remove(tabs.tabs[index])


def _activate_timefig():
    index = next((idx for idx, tab in enumerate(tabs.tabs) if tab.name == 'grafiek'),
                 None)

    tabs.active = index


def _create_timefig():
    logger.debug("bokeh: _update_time_fig")
    _remove_timefig()
    time_figs = []
    glymphs = data.timeseries.glymphs
    fig_height = int(height * 0.75 / len(glymphs))

    for idx, (key, values) in enumerate(glymphs.items()):
        if idx == 0:
            fig_title = data.timeseries.title
        else:
            fig_title = ""

        if idx == len(glymphs) - 1:
            x_axis_visible = True
        else:
            x_axis_visible = False

        if len(select_parameters.value) == 1:
            y_axis_label = select_parameters.value[0]
        else:
            fews_parameters = data.fews_api.parameters
            unit = fews_parameters.loc[fews_parameters["parameterGroup"] == key][
                "displayUnit"
            ].to_list()[0]
            y_axis_label = f"{key} [{unit}]"

        graph = data.timeseries.graphs[key]
        time_figs += [time_figure.generate(title=fig_title,
                                           width=int(width * 0.75),
                                           height=fig_height,
                                           x_axis_label=data.timeseries.x_axis_label,
                                           y_axis_label=y_axis_label,
                                           x_axis_visible=x_axis_visible,
                                           x_bounds=data.timeseries.x_bounds,
                                           y_bounds=graph['y_bounds'],
                                           glymphs=values,
                                           )]

    tabs.tabs.append(Panel(child=column(*time_figs),
                           title="grafiek",
                           name="grafiek")
                     )

    _activate_timefig()


def update_on_double_tap(event):
    """Reset selected locarions on double tab."""
    logger.debug("bokeh: update_on_double_tap")

    data.locations._update_selected([])
    select_locations.value = []


def update_on_tap(event):
    """Update when tap in map with location selected."""
    logger.debug("bokeh: update_on_tap")
    x, y = event.__dict__["x"], event.__dict__["y"]

    # update datamodel (locations selected)
    distance_threshold = (map_fig.x_range.end - map_fig.x_range.start) * 0.005
    data.update_map_tab(x, y, distance_threshold)

    # update locations filter
    select_locations.value = data.locations.selected_names


def update_on_filter_select(attrname, old, new):
    """Update when user selects different filter."""
    logger.debug("bokeh: update_on_filter_select")
    filter_selected = select_filter.value

    # update datamodel (filter,locations & parameters)
    data.update_filter_select(filter_selected)

    # clean locations filter
    select_locations.options = data.locations.names
    select_locations.value = []

    select_parameters.options = data.parameters.names
    select_parameters.value = []

    # reset the interface to map and remove timegraph
    _remove_timefig()
    tabs.active = 0


def update_on_locations_select(attrname, old, new):
    """Update when user selects in locations filter."""
    logger.debug("bokeh: update_on_locations_select")
    locations_select = select_locations.value

    # update datamodel (locations & parameters)
    data.update_locations_select(locations_select)

    # clean parameters filter
    select_parameters.options = data.parameters.names
    parameters_select = [val for val in
                         select_parameters.value
                         if val in data.parameters.names]

    select_parameters.value = parameters_select

    if locations_select and parameters_select:
        data.update_timeseries(locations_select, parameters_select)
        _create_timefig()


def update_on_parameters_select(attrname, old, new):
    """Update when user selects in parameter filter."""
    logger.debug("bokeh: update_on_parameters_select")

    parameters_select = select_parameters.value
    locations_select = select_locations.value

    if locations_select and parameters_select:
        data.update_timeseries(locations_select, parameters_select)
        _create_timefig()


logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# %% allow origin to server address
os.environ['BOKEH_ALLOW_WS_ORIGIN'] = SERVER

# %% define the data object
data = Data(FILTER_SELECTED, logger)

# %% detect server screen resolution
width, height = _screen_resolution()

# %% define map figure widget and handlers
map_glymphs = [
    {
        "type": "inverted_triangle",
        "size": 5,
        "source": data.locations.pluvial,
        "line_color": "blue",
        "fill_color": "white",
        "line_width": 1,
        "legend_label": "neerslag",
    },
    {
        "type": "inverted_triangle",
        "size": 5,
        "source": data.locations.other,
        "line_color": "orange",
        "fill_color": "white",
        "line_width": 1,
        "legend_label": "overig",
    },
    {"type": "circle",
     "size": 4,
     "source": data.locations.selected,
     "fill_color": "red"},
    ]

map_fig = map_figure.generate(
    width=int(width * 0.75),
    height=int(height * 0.75),
    bounds=data.locations.bounds,
    glymphs=map_glymphs,
    )

map_fig.on_event(events.Tap, update_on_tap)
map_fig.on_event(events.DoubleTap, update_on_double_tap)

# %% define filter selection and handlers
select_filter = Select(title="Filters:",
                       value=data.filters.selected['name'],
                       options=data.filters.names)

select_filter.on_change("value", update_on_filter_select)

# %% define location selection and handlers
select_locations = MultiSelect(title="Locations:",
                               value=[],
                               options=data.locations.names)
select_locations.height = int(height * 0.25)

select_locations.on_change("value", update_on_locations_select)

# %% define parameter selection and handlers
select_parameters = MultiSelect(title="Parameters:",
                                value=[],
                                options=data.parameters.names)

select_parameters.height = int(height * 0.25)

select_parameters.on_change("value", update_on_parameters_select)

# %% define layout
map_panel = Panel(child=map_fig, title="kaart", name="kaart")
tabs = Tabs(tabs=[map_panel])

layout = row(column(select_filter, select_locations, select_parameters), tabs)

curdoc().add_root(layout)
curdoc().title = TITLE
