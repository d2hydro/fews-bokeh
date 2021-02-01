"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from server_config import SERVER

from config import (
    TITLE,
    LOG_LEVEL,
    FILTER_SELECTED,
    SEARCH_YEARS,
    LOG_FILE
)

from fewsbokeh import map_figure, time_figure
import logging
from logging.handlers import RotatingFileHandler
from bokeh.plotting import figure
from bokeh import events
from bokeh.io import curdoc
from bokeh.models.widgets import (
    Div,
    Select,
    Panel,
    Tabs,
    MultiSelect,
    RangeSlider,
    Slider,
    DateRangeSlider
)
from bokeh.models import ColumnDataSource, Range1d
from bokeh.layouts import row, column, widgetbox
import ctypes
import numpy as np
import os

from datamodel import Data
import pandas as pd

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


def _datetime_offset(values, offset_years):
    offset_sign = np.sign(offset_years)
    return tuple(pd.Timestamp(val*1000000) + offset_sign * pd.DateOffset(
        years=abs(offset_years)) for val in values)


def _clean_filters():
    # clean parameters filter
    select_parameters.options = data.parameters.names
    parameters_select = [val for val in
                         select_parameters.value
                         if val in data.parameters.names]

    select_parameters.value = parameters_select


def _create_timefig():
    """Create a time-fig."""
    def _update_on_date_range(attrname, old, new):
        """Update triggered by date_range_sider."""
        start_datetime, end_datetime = date_range_slider.value_as_datetime

        patch_src.data.update({'x': [start_datetime,
                                     start_datetime,
                                     end_datetime,
                                     end_datetime],
                               'y': [lr_fig.y_range.start,
                                     lr_fig.y_range.end,
                                     lr_fig.y_range.end,
                                     lr_fig.y_range.start]})

    def _update_on_date_range_throttled(attrname, old, new):
        """Update triggered by date_range_sider throttled."""
        start_datetime, end_datetime = date_range_slider.value_as_datetime
        data.update_hr_timeseries(start_datetime, end_datetime)

    if all([select_locations.value,
       select_parameters.value]):
        data.create_timeseries(select_locations.value,
                               select_parameters.value)
        logger.debug("event: _create_time_fig")
        _remove_timefig()

        # update timeseries search select
        search_options = data.timeseries.timeseries["label"].to_list()
        search_options.sort()
        search_value = data.timeseries.timeseries.iloc[0]["label"]
        select_search_timeseries.options = search_options
        select_search_timeseries.value = search_value

        # difine top-figs
        top_figs = []
        glyphs = data.timeseries.hr_glyphs
        fig_height = int(height * 0.75 * 0.85 / len(glyphs))
        hr_x_range = Range1d(start=data.timeseries.x_bounds['start'],
                             end=data.timeseries.x_bounds['end'],
                             bounds="auto")
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
                unit = fews_parameters.loc[fews_parameters["parameterGroup"] == key][
                    "displayUnit"
                ].to_list()[0]
                y_axis_label = f"{key} [{unit}]"

            graph = data.timeseries.hr_graphs[key]
            top_figs += [time_figure.generate(title=fig_title,
                                              width=int(width * 0.75),
                                              height=fig_height,
                                              x_axis_label="",
                                              y_axis_label=y_axis_label,
                                              x_axis_visible=x_axis_visible,
                                              x_range=hr_x_range,
                                              y_bounds=graph['y_bounds'],
                                              glyphs=values,
                                              )]
        # define search fig
        glyph = data.timeseries.lr_glyph
        x_bounds = {"start": search_period_slider.value[0],
                    "end": search_period_slider.value[1]}

        y_bounds = {"start": 0, "end": 1}
        if len(glyph['source'].data['value']) > 0:
            y_bounds["start"] = glyph['source'].data['value'].min()
            y_bounds["end"] = glyph['source'].data['value'].max()

        lr_x_range = Range1d(start=x_bounds['start'],
                             end=x_bounds['end'],
                             bounds="auto")
        lr_fig = time_figure.generate(width=int(width * 0.75),
                                      height=int(height * 0.15 * 0.75),
                                      x_axis_label=data.timeseries.x_axis_label,
                                      y_axis_label="",
                                      x_axis_visible=True,
                                      x_range=lr_x_range,
                                      y_bounds=y_bounds,
                                      show_toolbar=False,
                                      glyphs=[glyph])

        patch_src = ColumnDataSource({'x': [data.timeseries.x_bounds["start"],
                                            data.timeseries.x_bounds["start"],
                                            data.timeseries.x_bounds["end"],
                                            data.timeseries.x_bounds["end"]],
                                      'y': [lr_fig.y_range.start,
                                            lr_fig.y_range.end,
                                            lr_fig.y_range.end,
                                            lr_fig.y_range.start]}
                                     )

        lr_fig.patch(x='x', y='y', source=patch_src, alpha=0.5, line_width=2)

        lr_fig.toolbar_location = None
        lr_fig.ygrid.visible = False
        lr_fig.yaxis[0].ticker = [y_bounds['start'], y_bounds['end']]
        lr_fig.ygrid[0].ticker = [y_bounds['start'], y_bounds['end']]

        # define daterange slider
        end_datetime = pd.Timestamp(search_period_slider.value[1]*1000000)
        start_datetime = end_datetime - pd.DateOffset(days=7)

        date_range_slider = DateRangeSlider(value=(start_datetime,
                                                   end_datetime),
                                            start=search_period_slider.value[0],
                                            end=search_period_slider.value[1],
                                            width=int(width * 0.75) - 80)

        date_range_slider.format = '%d-%m-%Y'
        date_range_slider.js_link('value', hr_x_range, 'start', attr_selector=0)
        date_range_slider.js_link('value', hr_x_range, 'end', attr_selector=1)
        date_range_slider.on_change("value", _update_on_date_range)
        date_range_slider.on_change("value_throttled", _update_on_date_range_throttled)

        search_period_slider.js_link('value', lr_x_range, 'start', attr_selector=0)
        search_period_slider.js_link('value', lr_x_range, 'end', attr_selector=1)
        search_period_slider.js_link('value',
                                     date_range_slider,
                                     'start',
                                     attr_selector=0)

        search_period_slider.js_link('value',
                                     date_range_slider,
                                     'end',
                                     attr_selector=1)

        tabs.tabs.append(Panel(child=column(*top_figs,
                                            lr_fig,
                                            row(Div(width=40, text=""),
                                                date_range_slider)),
                               title="grafiek",
                               name="grafiek"))


def update_on_double_tap(event):
    """Reset selected locarions on double tab."""
    logger.debug("event: update_on_double_tap")

    data.locations._update_selected([])
    select_locations.value = []


def update_on_tap(event):
    """Update when tap in map with location selected."""
    logger.debug("event: update_on_tap")
    x, y = event.__dict__["x"], event.__dict__["y"]

    # update datamodel (locations selected)
    distance_threshold = (map_fig.x_range.end - map_fig.x_range.start) * 0.005
    data.update_map_tab(x, y, distance_threshold)

    # update locations filter
    select_locations.value = data.locations.selected_names


def update_on_filter_select(attrname, old, new):
    """Update when user selects different filter."""
    logger.debug("event: update_on_filter_select")
    filter_selected = select_filter.value

    # update datamodel (filter,locations & parameters)
    data.update_filter_select(filter_selected)

    # clean locations filter
    select_locations.options = data.locations.names
    select_locations.value = []

    # clean filters
    _clean_filters()


def update_on_locations_select(attrname, old, new):
    """Update when user selects in locations filter."""
    logger.debug("event: update_on_locations_select")
    locations_select = select_locations.value

    # update datamodel (locations & parameters)
    data.update_locations_select(locations_select)

    # clean filters
    _clean_filters()

    # update timefig (if locs, pars are selected)
    _create_timefig()


def update_on_parameters_select(attrname, old, new):
    """Update when user selects in parameter filter."""
    logger.debug("event: update_on_parameters_select")

    # clean filters
    _clean_filters()

    # update timefig (if locs, pars,are selected)
    _create_timefig()


def update_on_search_select(attrname, old, new):
    """Update low lr graph when user updates any selection."""
    start_datetime, end_datetime = search_period_slider.value_as_datetime
    search_series = select_search_timeseries.value
    if search_series:
        data.update_lr_timeseries(search_series,
                                  start_datetime,
                                  end_datetime)


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
os.environ['BOKEH_ALLOW_WS_ORIGIN'] = SERVER

# %% define the data object
data = Data(FILTER_SELECTED, logger)

# %% detect server screen resolution
width, height = _screen_resolution()

# %% define map figure widget and handlers
map_glyphs = [
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
    glyphs=map_glyphs,
    )

map_fig.on_event(events.Tap, update_on_tap)
map_fig.on_event(events.DoubleTap, update_on_double_tap)

# %% define filter selection and handlers
select_filter = Select(title="Filters:",
                       value=data.filters.selected['name'],
                       options=data.filters.names)

select_filter.on_change("value", update_on_filter_select)

# %% define location selection and handlers
select_locations = MultiSelect(title="Locaties:",
                               value=[],
                               options=data.locations.names)
select_locations.height = int(height * 0.25)

select_locations.on_change("value", update_on_locations_select)

# %% define parameter selection and handlers
select_parameters = MultiSelect(title="Parameters:",
                                value=[],
                                options=data.parameters.names)

select_parameters.height = int(height * 0.13)

select_parameters.on_change("value", update_on_parameters_select)

# %% define search period selection
search_period_slider = DateRangeSlider(value=(data.search_start_datetime,
                                              data.end_datetime),
                                       start=data.first_value_datetime,
                                       end=data.end_datetime,
                                       title="Zoekperiode")

search_period_slider.format = '%d-%m-%Y'
search_period_slider.on_change("value_throttled", update_on_search_select)

select_search_timeseries = Select(title="Zoektijdserie:", value=None, options=[])
select_search_timeseries.on_change("value", update_on_search_select)


# %% define layout

map_panel = Panel(child=map_fig, title="kaart", name="kaart")
tabs = Tabs(tabs=[map_panel])

div = Div(text="""<p style="color:red"><b>Let op! Deze app is in nog in ontwikkeling!
          (laatste update: 28-01-2021)<b></p>""", height=int(height * 0.05))

layout = column(div, row(column(select_filter,
                                select_locations,
                                select_parameters,
                                search_period_slider,
                                select_search_timeseries), tabs))


curdoc().add_root(layout)
curdoc().title = TITLE

# location_ids, parameter_ids, filter_id, parameter_groups = [
#     ['4120'], ['Q.meting.m3uur'], 'Hydronet_Keten', ['Debiet m3 per uur']]

# data.timeseries.create(location_ids, parameter_ids, filter_id, parameter_groups)

# search_parameters = data.get_search_timeseries()
# select_search_timeseries.options = search_parameters[0]
# select_search_timeseries.value = search_parameters[1]

# # difine top-figs
# top_figs = []
# glyphs = data.timeseries.hr_glyphs
# fig_height = int(height * 0.75 * 0.85 / len(glyphs))
# hr_x_range = Range1d(start=data.timeseries.x_bounds['start'],
#                      end=data.timeseries.x_bounds['end'],
#                      bounds="auto")
# for idx, (key, values) in enumerate(glyphs.items()):
#     if idx == 0:
#         fig_title = ",".join(select_locations.value)
#     else:
#         fig_title = ""

#     if idx == len(glyphs.items()) - 1:
#         x_axis_visible = True
#     else:
#         x_axis_visible = False

#     if len(select_parameters.value) == 1:
#         y_axis_label = select_parameters.value[0]
#     else:
#         fews_parameters = data.fews_api.parameters
#         unit = fews_parameters.loc[fews_parameters["parameterGroup"] == key][
#             "displayUnit"
#         ].to_list()[0]
#         y_axis_label = f"{key} [{unit}]"

#     graph = data.timeseries.hr_graphs[key]
#     top_figs += [time_figure.generate(title=fig_title,
#                                       width=int(width * 0.75),
#                                       height=fig_height,
#                                       x_axis_label="",
#                                       y_axis_label=y_axis_label,
#                                       x_axis_visible=x_axis_visible,
#                                       x_range=hr_x_range,
#                                       y_bounds=graph['y_bounds'],
#                                       glyphs=values,
#                                       )]
# # define search fig
# glyph = data.timeseries.lr_glyph
# x_bounds = {"start": search_period_slider.value[0],
#             "end": search_period_slider.value[1]}

# y_bounds = {"start": 0, "end": 1}
# if len(glyph['source'].data['value']) > 0:
#     y_bounds["start"] = glyph['source'].data['value'].min()
#     y_bounds["end"] = glyph['source'].data['value'].max()

# lr_x_range = Range1d(start=x_bounds['start'],
#                      end=x_bounds['end'],
#                      bounds="auto")
# lr_fig = time_figure.generate(width=int(width * 0.75),
#                               height=int(height * 0.15 * 0.75),
#                               x_axis_label=data.timeseries.x_axis_label,
#                               y_axis_label="",
#                               x_axis_visible=True,
#                               x_range=lr_x_range,
#                               y_bounds=y_bounds,
#                               show_toolbar=False,
#                               glyphs=[glyph])

# patch_src = ColumnDataSource({'x': [data.timeseries.x_bounds["start"],
#                                     data.timeseries.x_bounds["start"],
#                                     data.timeseries.x_bounds["end"],
#                                     data.timeseries.x_bounds["end"]],
#                               'y': [lr_fig.y_range.start,
#                                     lr_fig.y_range.end,
#                                     lr_fig.y_range.end,
#                                     lr_fig.y_range.start]}
#                              )

# lr_fig.patch(x='x', y='y', source=patch_src, alpha=0.5, line_width=2)

# lr_fig.toolbar_location = None
# lr_fig.ygrid.visible = False
# lr_fig.yaxis[0].ticker = [y_bounds['start'], y_bounds['end']]
# lr_fig.ygrid[0].ticker = [y_bounds['start'], y_bounds['end']]

# # define daterange slider
# end_datetime = pd.Timestamp(search_period_slider.value[1]*1000000)
# start_datetime = end_datetime - pd.DateOffset(days=7)

# fig = figure()
# source = ColumnDataSource(data={'datetime':[data.start_datetime, data.end_datetime],'value':[0,1]})
# fig.line(x="datetime", y="value", source=source)

# curdoc().add_root(fig)
# curdoc().title = TITLE
