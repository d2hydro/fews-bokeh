# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""


from bokeh.models import HoverTool, Range1d
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors


def generate(width=None,
             height=None,
             bounds=None,
             glyphs=None,
             active_scroll="wheel_zoom"):
    """Map-figure from supplied bokeh input parameters."""
    x_range = Range1d(start=bounds[0],
                      end=bounds[2],
                      bounds=None)

    y_range = Range1d(start=bounds[1],
                      end=bounds[3],
                      bounds=None)

    map_hover = HoverTool(tooltips=[("shortName", "@shortName"),
                                    ("locationId", "@locationId")
                                    ])

    tools = ["wheel_zoom", "pan", "reset", map_hover]

    map_fig = figure(tools=tools,
                     active_scroll=active_scroll,
                     height=height,
                     width=width,
                     x_range=x_range,
                     y_range=y_range)

    map_fig.axis.visible = False
    map_fig.toolbar.autohide = True

    tile_provider = get_provider(Vendors.CARTODBPOSITRON)
    map_fig.add_tile(tile_provider, name="background")

    if glyphs:
        for glyph in glyphs:
            glyph_type = glyph["type"]
            glyph.pop("type")
            getattr(map_fig, glyph_type)(**glyph)
        map_fig.legend.click_policy = "hide"

    return map_fig
