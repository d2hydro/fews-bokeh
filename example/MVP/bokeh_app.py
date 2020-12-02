# -*- coding: utf-8 -*-
"""
Created on Tue Dec  1 13:13:25 2020

@author: danie
"""

from fewsbokeh import fews_rest
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd

from bokeh import events
from bokeh.io import curdoc
from bokeh.models.widgets import Select,Div,Panel,Tabs
from bokeh.models import ColumnDataSource,GeoJSONDataSource,DatetimeTickFormatter,Tool,Range1d
from bokeh.core.properties import String
from bokeh.layouts import row,column
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors
from shapely.geometry import Point
import ctypes
import json

url =  'https://fewsvechtdb.lizard.net/FewsWebServices/rest/fewspiservice/v1/'
thinner = None
map_buffer = 1000
start_time = pd.Timestamp(year=2020,month=1,day=1)
end_time = pd.Timestamp.now()


def screen_resolution():
    '''computes server screen resolution'''
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))
    
    return width,height

def update_plot_from_geo(event):
    '''update time_graph with location selected'''
    x, y = event.__dict__['x'],event.__dict__['y']
    distance_threshold = (map_x_range.end - map_x_range.start) * 0.05
    gdf['distance'] = gdf['geometry'].distance(Point(x,y))
    gdf_dist = gdf.loc[gdf['distance'] < distance_threshold]
    if not gdf_dist.empty:
        location_id = gdf_dist.sort_values('distance').iloc[0]['locationId']

        df = fews_rest.get_timeseries(url,
                                      locationIds = location_id,
                                      parameterIds = 'H.meting',
                                      startTime = start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                      endTime = end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                      thinning = thinner)
        
        if not df is None:
    
            src = ColumnDataSource(data=df)
            time_src.data.update(src.data)
        
            time_fig.title.text = df.location
            time_x_range.start = df["datetime"].min()
            time_x_range.end = df["datetime"].max()           
            
            time_y_range.start = df["value"].min()
            time_y_range.end = df["value"].max()
            
            tabs.active = 1   

time_df = pd.DataFrame({'datetime':[],'value':[]})
time_df.location = ''
time_df.time_zone = '0'
time_df.parameter = ''
time_df.units = ''

time_src = ColumnDataSource(data=time_df)

gdf = fews_rest.get_locations(url,filterId='HW_WVS')
geo_src = GeoJSONDataSource(geojson=gdf.to_json())

width,height = screen_resolution()

timespan = (end_time - start_time).days
thinner = int(timespan * 86400 * 1000 / width)

time_x_range = Range1d(start=start_time, end=end_time, bounds=None)
time_y_range = Range1d(start=0, end=1, bounds=None)

time_fig = figure(title = time_df.location,
                  tools=['pan','box_zoom','wheel_zoom','reset','save'],
                  active_drag=None,
                  height = int(height *0.75),
                  width = int(width * 0.75),
                  x_axis_label = 'datum [gmt {0:+}]'.format(int(float(time_df.time_zone))),
                  y_axis_label = f'{time_df.parameter} [{time_df.units}]',
                  x_range=time_x_range,
                  y_range=time_y_range
                  )

time_fig.toolbar.autohide = True
time_fig.title.align = 'center'
  
time_fig.xaxis.formatter=DatetimeTickFormatter(hours=["%H:%M:%S"],
                                          days=["%Y-%m-%d"],
                                          months=["%Y-%m-%d"],
                                          years=["%Y-%m-%d"],
                                          )

time_fig.line(x='datetime',y='value',color = 'blue',source = time_src)

xmin,ymin,xmax,ymax = gdf['geometry'].buffer(map_buffer).total_bounds
map_x_range = Range1d(start=xmin, end=xmax, bounds=None)
map_y_range = Range1d(start=ymin, end=ymax, bounds=None)

map_fig = figure(tools='wheel_zoom,pan', 
          active_scroll="wheel_zoom",
          height = int(height *0.75),
          width = int(width * 0.75),
          x_range = map_x_range,
          y_range = map_y_range
          )
map_fig.axis.visible = False
map_fig.toolbar.autohide = True

tile_provider = get_provider(Vendors.CARTODBPOSITRON)
map_fig.add_tile(tile_provider,name='background')

map_fig.circle('x', 'y', 
               size=5, 
               source=geo_src, 
               line_color="blue", 
               fill_color="white", 
               line_width=2)

map_fig.on_event(events.Tap, update_plot_from_geo)

tabs = Tabs(tabs=[Panel(child=map_fig, title="kaart"),
                  Panel(child=time_fig, title="grafiek")]
            )

layout = column(tabs)

curdoc().add_root(layout)
curdoc().title = 'Bokeh FEWS-REST client'