# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""

from bokeh.models  import HoverTool, BBoxTileSource
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors


    
def generate(width,
             height,
             x_range,
             y_range,
             glymphs=None,
             active_scroll = "wheel_zoom"):
    '''generates a map-figure from supplied bokeh input parameters'''
    
    map_hover = HoverTool(tooltips = [('shortName', '@shortName'),
                              ('locationId', '@locationId')
                              ])
    
    tools=['wheel_zoom','pan','reset',map_hover]

    map_fig = figure(tools = tools, 
                     active_scroll=active_scroll,
                     height = height,
                     width = width,
                     x_range = x_range,
                     y_range = y_range)
    
    map_fig.axis.visible = False
    map_fig.toolbar.autohide = True
    
    
    tile_provider = get_provider(Vendors.CARTODBPOSITRON)
    map_fig.add_tile(tile_provider,name='background')
    
    if glymphs:
        for glymph in glymphs:
            glymph_type = glymph['type']
            glymph.pop('type')
            getattr(map_fig,glymph_type)(**glymph)
        map_fig.legend.click_policy="hide"
           
            
    return map_fig