# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""

from bokeh.models  import HoverTool, DatetimeTickFormatter, Range1d
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors


def generate(width,
             height,
             x_bounds,
             y_bounds,
             title="",
             x_axis_visible=True,
             x_axis_label="",
             y_axis_label="",
             glyphs=None):
    """Generate a time-figure from supplied bokeh input parameters."""
    time_hover = HoverTool(tooltips=[("datetime", "@datetime{%F}"),
                                     ("value", "@value")],
                           formatters={"@datetime": "datetime"})

    tools = ["pan", "box_zoom", "xwheel_zoom", "reset", time_hover, "save"]

    x_range = Range1d(start=x_bounds['start'], end=x_bounds['end'], bounds="auto")
    y_range = Range1d(start=y_bounds['start'], end=y_bounds['end'], bounds="auto")
    time_fig = figure(title=title,
                      tools=tools,
                      active_drag=None,
                      height=height,
                      width=width,
                      x_axis_label=x_axis_label,
                      y_axis_label=y_axis_label,
                      x_range=x_range,
                      y_range=y_range)

    time_fig.toolbar.autohide = False
    time_fig.title.align = "center"

    time_fig.xaxis.formatter=DatetimeTickFormatter(hours=["%H:%M:%S"],
                                                   days=["%Y-%m-%d"],
                                                   months=["%Y-%m-%d"],
                                                   years=["%Y-%m-%d"],
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
