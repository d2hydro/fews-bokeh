# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""

from bokeh.models  import HoverTool, DatetimeTickFormatter, Range1d
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors


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
             glyphs=None):
    """Generate a time-figure from supplied bokeh input parameters."""
    time_hover = HoverTool(tooltips=[("datum-tijd", "@datetime{%F}"),
                                     ("waarde", "@value{(0.00)}")],
                           formatters={"@datetime": "datetime"})

    tools = ["pan", "box_zoom", "xwheel_zoom", "reset", time_hover, "save"]

    if not x_range:
        x_range = Range1d(start=x_bounds['start'],
                          end=x_bounds['end'],
                          bounds=bound_limits)
    if not y_range:
        y_range = Range1d(start=y_bounds['start'],
                          end=y_bounds['end'],
                          bounds=bound_limits)
    time_fig = figure(title=title,
                      tools=tools,
                      # active_drag=None,
                      height=height,
                      width=width,
                      sizing_mode=sizing_mode,
                      x_axis_label=x_axis_label,
                      y_axis_label=y_axis_label,
                      x_range=x_range,
                      y_range=y_range)

    time_fig.toolbar.autohide = False
    time_fig.title.align = "center"

    time_fig.xaxis.formatter = DatetimeTickFormatter(hours=["%H:%M"],
                                                     days=["%d-%m-%Y"],
                                                     months=["%d-%m-%Y"],
                                                     years=["%d-%m-%Y"],
                                                     )
    time_fig.xaxis.visible = x_axis_visible

    if glyphs:
        for glyph in glyphs:
            glyph_type = glyph["type"]
            glyph.pop("type")
            getattr(time_fig, glyph_type)(x="datetime", y="value", **glyph)

        if next((True for glyph in glyphs if "legend_label" in glyph.keys()), False):
            time_fig.legend.click_policy = "hide"

    return time_fig
