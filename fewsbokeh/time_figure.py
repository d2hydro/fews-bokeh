# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""

from bokeh.models  import HoverTool, DatetimeTickFormatter, Range1d, Legend, PanTool, BoxZoomTool, WheelZoomTool
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors
import pandas as pd

def generate(width=None,
             height=None,
             sizing_mode=None,
             x_bounds=None,
             y_bounds=None,
             x_range=None,
             y_range=None,
             title="",
             x_axis_visible=True,
             x_axis_label="",
             y_axis_label="",
             show_toolbar=True,
             bound_limits=None,
             glyphs=None,
             active_scroll="xwheel_zoom",
             active_drag="box_zoom",
             save_tool="save",
             toolbar_location="above",
             title_visible=False,
             ):
         
    """Generate a time-figure from supplied bokeh input parameters."""
    time_hover = HoverTool(tooltips=[("datum-tijd", "@datetime{%F}"),
                                     ("waarde", "@value{(0.00)}")],
                           formatters={"@datetime": "datetime"})
    
    time_hover.toggleable = False

#    pan_tool = PanTool()
    tools = ["pan",
             "box_zoom",
             "xwheel_zoom",
             "zoom_in",
             "zoom_out",
             "reset",
             "undo",
             "redo",
             save_tool,
             time_hover]

    if not x_range:
        x_range = Range1d(start=x_bounds['start'],
                          end=x_bounds['end'],
                          bounds=bound_limits)
    x_range.min_interval=pd.Timedelta(hours=1)

    if not y_range:
        y_range = Range1d(start=y_bounds['start'],
                          end=y_bounds['end'],
                          bounds=bound_limits)
    y_range.min_interval=0.1
    time_fig = figure(title=title,
                      tools=tools,
                      height=height,
                      width=width,
                      sizing_mode=sizing_mode,
                      x_axis_label=x_axis_label,
                      y_axis_label=y_axis_label,
                      x_range=x_range,
                      y_range=y_range,
                      active_scroll=active_scroll,
                      active_drag=active_drag,
                      toolbar_location=toolbar_location,
                      )

    wheel_zoom = next((i for i in time_fig.tools if type(i) == WheelZoomTool), None)
    if wheel_zoom:
        wheel_zoom.speed = 0.0001
        
    time_fig.toolbar.logo = None
    time_fig.toolbar.autohide = False

    time_fig.title.align = "center"
    
    time_fig.xaxis.formatter = DatetimeTickFormatter(hours=["%H:%M"],
                                                     days=["%d-%m-%Y"],
                                                     months=["%d-%m-%Y"],
                                                     years=["%d-%m-%Y"],
                                                     )
    time_fig.xaxis.visible = x_axis_visible
    time_fig.title.visible = title_visible

    if glyphs:
        for glyph in glyphs:
            glyph_type = glyph["type"]
          
            glyph.pop("type")
            getattr(time_fig, glyph_type)(x="datetime", y="value", **glyph)

        if next((True for glyph in glyphs if "legend_label" in glyph.keys()), False):
            time_fig.legend.click_policy = "hide"
     
            time_fig.add_layout(time_fig.legend[0], "right")
            time_fig.legend[0].label_text_font_size = "9pt"
    return time_fig
