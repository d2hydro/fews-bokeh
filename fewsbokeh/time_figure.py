# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:59:08 2020

@author: danie
"""

from bokeh.models  import HoverTool, DatetimeTickFormatter
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors



def generate(width,
             height,
             x_range,
             y_range,
             title='',
             x_axis_visible=True,
             x_axis_label='',
             y_axis_label='',
             glymphs=None):
    '''generates a time-figure from supplied bokeh input parameters'''
    
    time_hover = HoverTool(tooltips=[('datetime', '@datetime{%F}'),
                                      ('value', '@value')],
                            formatters={'@datetime': 'datetime'})
    
    tools=['pan','box_zoom','xwheel_zoom','reset',time_hover,'save']
    
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
    time_fig.title.align = 'center'
      
    time_fig.xaxis.formatter=DatetimeTickFormatter(hours=["%H:%M:%S"],
                                                   days=["%Y-%m-%d"],
                                                   months=["%Y-%m-%d"],
                                                   years=["%Y-%m-%d"],
                                                   )
    time_fig.xaxis.visible = x_axis_visible
    
    
    
    if glymphs:
        for glymph in glymphs:
            glymph_type = glymph['type']
            glymph.pop('type')
            getattr(time_fig,glymph_type)(x='datetime',y='value', **glymph)
            
        time_fig.legend.click_policy="hide"
    
    return time_fig