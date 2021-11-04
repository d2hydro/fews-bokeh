# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""


from bokeh.models import HoverTool, Range1d, BBoxTileSource, WMTSTileSource, Legend, LegendItem, TapTool
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors

URLS = {"luchtfoto": {"url": ("https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?"
                      "service=WMS&version=1.3.0&request=GetMap&layers=Actueel_ortho25"
                      "&width=265&height=265&styles=&crs=EPSG:3857&format=image/jpeg"
                      "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"),
                      "class": BBoxTileSource},
        "topografie": {"url": ("https://geodata.nationaalgeoregister.nl/tiles/service/wmts/"
                "brtachtergrondkaart/EPSG:3857/{z}/{x}/{y}.png"),
               "class": WMTSTileSource}
        }

def get_tileource(layer, urls=URLS):
    if layer == "background":
        return get_provider(Vendors.CARTODBPOSITRON)
    elif layer in urls.keys():
        url = urls[layer]["url"]
        if "args" in urls[layer]:
            args = urls[layer]["args"]
        else:
            args = {}
        return urls[layer]["class"](url=url, **args)   

def generate(width=None,
             height=None,
             bounds=None,
             glyphs=None,
             background="background",
             map_layers= {},
             save_tool="save",
             active_scroll="wheel_zoom",
             toolbar_location="above"):
    """Map-figure from supplied bokeh input parameters."""
    x_range = Range1d(start=bounds[0],
                      end=bounds[2],
                      bounds=None)

    y_range = Range1d(start=bounds[1],
                      end=bounds[3],
                      bounds=None)

    map_hover = HoverTool(tooltips=[("Locatie", "@shortName"),
                                    ("ID", "@locationId")
                                    ])
    
    map_hover.toggleable = False

    tools = ["tap", "wheel_zoom", "pan", "reset", map_hover, save_tool]

    map_fig = figure(tools=tools,
                     active_scroll=active_scroll,
                     height=height,
                     width=width,
                     x_range=x_range,
                     y_range=y_range,
                     toolbar_location=toolbar_location)

    map_fig.axis.visible = False
    map_fig.toolbar.logo = None
    map_fig.toolbar.autohide = True
    
    map_fig.select(type=TapTool)

    # add background
    tile_source = get_tileource(background)
    map_fig.add_tile(tile_source, name="background")

    # add additionalmap_layers if any
    if map_layers:
        layer_names = list(map_layers.keys())
        layer_names.reverse()
        for layer_name in layer_names:
            tile_source = get_tileource(layer_name, urls=map_layers)
            if "alpha" in map_layers[layer_name].keys():
                alpha = map_layers[layer_name]["alpha"]
            else:
                alpha = 1
            map_fig.add_tile(tile_source,
                             name=layer_name,
                             visible=map_layers[layer_name]["visible"],
							 alpha=alpha)

    if glyphs:
        for glyph in glyphs:
            glyph_type = glyph["type"]
            glyph.pop("type")
            getattr(map_fig, glyph_type)(**glyph)
        map_fig.legend.click_policy = "hide"

    return map_fig
