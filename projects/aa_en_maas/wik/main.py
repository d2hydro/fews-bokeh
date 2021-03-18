"""Bokeh FEWS-REST dashboard for WIK Aa en Maas."""
from server_config import SERVER, USE_JINJA_TEMPLATE

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
from bokeh.events import PanEnd
from bokeh.models.widgets import (
    Div,
    Button,
    Select,
    Panel,
    Tabs,
    MultiSelect,
    RangeSlider,
    DatePicker,
    Slider,
    DateRangeSlider,
    HTMLTemplateFormatter
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

if USE_JINJA_TEMPLATE==False:

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


def _create_time_col(time_figs):
    for fig in time_figs:
        fig.height = int(height * 0.78 * 0.75 / len(time_figs))
        fig.width = int(width * 0.75)

    time_col = column(time_figs)
    time_col.children.append(search_fig)
    # time_col.children.append(period_slider)
    time_col.children.append(row(Div(width=40, text=""),
                                 period_slider))

    return time_col


def _create_timefig():
    """Create a time-fig."""
    if all([select_locations.value,
       select_parameters.value]):
        # print(select_locations.value, select_parameters.value)
        data.create_timeseries(select_locations.value,
                               select_parameters.value)

        logger.debug("event: _create_time_fig")

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
                        fews_parameters["parameterGroup"] == key][
                            "displayUnit"].to_list()[0]
                    y_axis_label = f"{key} [{unit}]"

                graph = data.timeseries.hr_graphs[key]
                top_figs += [time_figure.generate(title=fig_title,
                                                  sizing_mode="stretch_both",
                                                  x_axis_label="",
                                                  y_axis_label=y_axis_label,
                                                  x_axis_visible=x_axis_visible,
                                                  x_range=time_figs_x_range,
                                                  y_range=graph['y_range'],
                                                  glyphs=values,
                                                  )]

            # register PanEnd event on all plots
            for plot in top_figs:
                plot.on_event(PanEnd, update_on_top_figs_tools)
       
            # update search-data
            ts_labels = data.timeseries.timeseries["label"].to_list()
            select_search_timeseries.options = ts_labels
            select_search_timeseries.value = ts_labels[0]

            # update layout
   #         search_fig.yaxis[0].ticker = [data.timeseries.lr_y_range.start,
  #                                        data.timeseries.lr_y_range.end]

  #          search_fig.ygrid[0].ticker = [data.timeseries.lr_y_range.start,
  #                                        data.timeseries.lr_y_range.end]
            ts_labels = data.timeseries.timeseries["label"].to_list()
            time_col = _create_time_col(top_figs)
            if USE_JINJA_TEMPLATE==False:
                _remove_timefig()
                tabs.tabs.append(Panel(child=time_col,
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
    logger.debug("event: update_on_search_select")
    start_datetime = pd.Timestamp(search_start_date_picker.value)
    end_datetime = pd.Timestamp(search_end_date_picker.value)
    search_series = select_search_timeseries.value
    if search_series:
        data.update_lr_timeseries(search_series,
                                  start_datetime,
                                  end_datetime)


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
                start_datetime, start_datetime + pd.Timedelta(days=150))
        else:
            period_slider.value = (
                end_datetime - pd.Timedelta(days=150), end_datetime)


def update_on_period(attrname, old, new):
    """Update triggered by date_range_sider."""
    # logger.debug("event: update_on_period")
    start_datetime, end_datetime = period_slider.value_as_datetime

    days = (end_datetime - start_datetime).days
    if days > 90:
        if old[0] != new[0]:
            # starttime is shifting
            period_slider.value = (
                start_datetime, start_datetime + pd.Timedelta(days=90))
        else:
            period_slider.value = (
                end_datetime - pd.Timedelta(days=90), end_datetime)

    patch_src.data.update({'x': [period_slider.value[0],
                                 period_slider.value[0],
                                 period_slider.value[1],
                                 period_slider.value[1]],
                           'y': [search_fig.y_range.start,
                                 search_fig.y_range.end,
                                 search_fig.y_range.end,
                                 search_fig.y_range.start]})


def update_on_top_figs_tools(event):
    """Update triggered by date_range_sider throttled."""
    logger.debug("event: update_on_period_select")
    start_datetime = pd.Timestamp(time_figs_x_range.start * 10**6)
    end_datetime = pd.Timestamp(time_figs_x_range.end * 10**6)
    data.update_hr_timeseries(start_datetime, end_datetime)

    period_slider.value = (start_datetime, end_datetime)
    # patch_src.data.update({'x': [start_datetime,
    #                              start_datetime,
    #                              end_datetime,
    #                              end_datetime],
    #                        'y': [search_fig.y_range.start,
    #                              search_fig.y_range.end,
    #                              search_fig.y_range.end,
    #                              search_fig.y_range.start]})
    # time_figs_x_range.reset_start = start_datetime
    # time_figs_x_range.reset_end = end_datetime


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
    bounds=data.locations.bounds,
    glyphs=map_glyphs,
    )

map_fig.name = "map_fig"
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

select_locations.on_change("value", update_on_locations_select)

# %% define parameter selection and handlers
select_parameters = MultiSelect(title="Parameters:",
                                value=[],
                                options=data.parameters.names)


select_parameters.on_change("value", update_on_parameters_select)

# %% define search period selection
# search_period_slider = DateRangeSlider(value=(data.search_start_datetime,
#                                              data.now),
#                                       start=data.first_value_datetime,
#                                       end=data.now,
#                                       title="Zoekperiode")

search_start_date_picker = DatePicker(
    title='start datum',
    value=data.search_start_datetime.strftime('%Y-%m-%d'),
    min_date=data.first_value_datetime.strftime('%Y-%m-%d'),
    max_date=data.search_start_datetime.strftime('%Y-%m-%d')
    )

search_end_date_picker = DatePicker(
    title='eind datum',
    value=data.now.strftime('%Y-%m-%d'),
    min_date=data.search_start_datetime.strftime('%Y-%m-%d'),
    max_date=data.now.strftime('%Y-%m-%d')
    )


search_start_date_picker.on_change("value", update_search_range)
search_end_date_picker.on_change("value", update_search_range)

search_button = Button(label="update zoekgrafiek", button_type="success")
search_button.on_click(update_search_fig)

# search_period_slider.format = '%d-%m-%Y'
# search_period_slider.on_change("value", update_on_search_period)
# search_period_slider.on_change("value_throttled", update_on_search_select)

select_search_timeseries = Select(title="Zoektijdserie:", value=None, options=[])
select_search_timeseries.on_change("value", update_on_search_select)

# %% define empty time_figs

time_figs_x_range = Range1d(start=data.timeseries.start_datetime,
                            end=data.timeseries.end_datetime)

time_figs_y_range = Range1d(start=-1,
                            end=1,
                            bounds="auto")


time_figs = [time_figure.generate(
    title="selecteer locatie en paramameter",
    y_axis_label="-",
    x_range=time_figs_x_range,
    y_range=time_figs_y_range)]

search_range = Range1d(start=pd.Timestamp(search_start_date_picker.value),
                       end=pd.Timestamp(search_end_date_picker.value),
                       bounds="auto")

search_fig = time_figure.generate(x_axis_label=data.timeseries.x_axis_label,
                                  y_axis_label="",
                                  x_axis_visible=True,
                                  x_range=search_range,
                                  y_range=data.timeseries.lr_y_range,
                                  show_toolbar=False,
                                  glyphs=[data.timeseries.lr_glyph])

search_fig.toolbar_location = None
search_fig.ygrid.visible = False
search_fig.yaxis[0].ticker = [data.timeseries.lr_y_range.start,
                              data.timeseries.lr_y_range.end]

search_fig.ygrid[0].ticker = [data.timeseries.lr_y_range.start,
                              data.timeseries.lr_y_range.end]

patch_src = ColumnDataSource({'x': [data.timeseries.start_datetime,
                                    data.timeseries.start_datetime,
                                    data.timeseries.end_datetime,
                                    data.timeseries.end_datetime],
                              'y': [search_fig.y_range.start,
                                    search_fig.y_range.end,
                                    search_fig.y_range.end,
                                    search_fig.y_range.start]}
                             )

search_fig.patch(x='x', y='y', source=patch_src, alpha=0.5, line_width=2)

period_slider = DateRangeSlider(value=(data.timeseries.start_datetime,
                                       data.timeseries.end_datetime),
                                start=data.timeseries.search_start_datetime,
                                end=data.timeseries.search_end_datetime)
period_slider.format = '%d-%m-%Y'


# search_start_date_picker.js_link('value', search_range, 'start')
# search_end_date_picker.js_link('value', search_range, 'end')

# search_period_slider.js_link('value', search_range, 'start', attr_selector=0)
# search_period_slider.js_link('value', search_range, 'end', attr_selector=1)
# search_period_slider.js_link('value',
#                              period_slider,
#                              'start',
#                              attr_selector=0)

# search_period_slider.js_link('value',
#                              period_slider,
#                              'end',
#                              attr_selector=1)

period_slider.on_change("value", update_on_period)
period_slider.on_change("value_throttled", update_on_period_select)
period_slider.js_link('value', time_figs_x_range, 'start', attr_selector=0)
period_slider.js_link('value', time_figs_x_range, 'end', attr_selector=1)

# %% define layout
width = 1920 * 0.82
height = 1080 * 0.82
div = Div(text="""<p style="color:red"><b>Let op! Deze app is in nog in ontwikkeling!
          (laatste update: 16-03-2021)<b></p>""", height=int(height * 0.05))

if USE_JINJA_TEMPLATE:

    
#    search_fig = column(Div(text="grafiek_lr"),name="grafiek_lr",sizing_mode="stretch_both")
#    grafiek_slider = column(,name="grafiek_slider",sizing_mode="stretch_both")
    
    filters = column(select_filter, name="filters", sizing_mode= "stretch_both")
    locaties = column(select_locations, name="locaties", sizing_mode= "stretch_both")
    parameters = column(select_parameters, name="parameters", sizing_mode= "stretch_both")
    start_datepicker = column(search_start_date_picker, name="start_datepicker", sizing_mode= "stretch_both")
    end_datepicker = column(search_end_date_picker, name="end_datepicker", sizing_mode= "stretch_both")
    search_button = column(search_button, name="search_button", sizing_mode= "stretch_both")
    zoektijdserie = column(div, select_search_timeseries, name="zoektijdserie", sizing_mode= "stretch_both")
    kaart = column(map_fig,name="kaart",sizing_mode="stretch_both")
    grafiek = column(time_figs, name = "grafiek", sizing_mode="stretch_both")
    lr_fig = column(search_fig,name="grafiek_lr",sizing_mode="stretch_both")
    slider = column(period_slider,name="slider",sizing_mode="stretch_both")
    
    curdoc().add_root(filters)
    curdoc().add_root(locaties)
    curdoc().add_root(parameters)
    curdoc().add_root(start_datepicker)
    curdoc().add_root(end_datepicker)
    curdoc().add_root(search_button)  
    curdoc().add_root(zoektijdserie)
    curdoc().add_root(kaart)
    curdoc().add_root(grafiek)
    curdoc().add_root(lr_fig)
    curdoc().add_root(slider)

else:
    select_locations.size = 10
    map_fig.sizing_mode = "stretch_both"
    map_panel = Panel(child=map_fig, title="kaart", name="kaart")
    search_fig.width = int(width * 0.75)
    search_fig.height = int(height * 0.15 * 0.75)
    period_slider.width = int(width * 0.75 - 80)
    period_slider.align = "center"

    time_col = _create_time_col(time_figs)

    time_col.align = 'end'

    time_panel = Panel(child=time_col,
                       title="grafiek",
                       name="grafiek")
    tabs = Tabs(tabs=[map_panel, time_panel],
                name="tabs")

#    search_start_date_picker.width = int(width * 0.08)
#    search_end_date_picker.width = int(width * 0.08)
#    search_button.width = int(width * 0.2)
    search_start_date_picker.sizing_mode = "stretch_both"
    search_end_date_picker.sizing_mode = "stretch_both"
    search_button.sizing_mode = "stretch_width"
    search_period_control = column(row(
        search_start_date_picker,
        search_end_date_picker),
        search_button)

    search_period_control.width = int(width * 0.2)
    controls = column(div,
                      select_filter,
                      select_locations,
                      select_parameters,
                      search_period_control,
                      select_search_timeseries)
    controls.height = int(height * 0.75 - 80)
    layout = row(controls, tabs)

    curdoc().add_root(layout)
    curdoc().title = TITLE
