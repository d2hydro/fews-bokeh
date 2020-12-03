# -*- coding: utf-8 -*-
"""
Created on Tue Dec  1 13:13:25 2020

@author: danie
"""

from config import *
from fewsbokeh import fews_rest
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd

from bokeh import events
from bokeh.io import curdoc
from bokeh.models.widgets import Select,Div,Panel,Tabs,MultiSelect
from bokeh.models import ColumnDataSource,GeoJSONDataSource,DatetimeTickFormatter,Tool,Range1d,HoverTool
from bokeh.core.properties import String
from bokeh.layouts import row,column
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors
from shapely.geometry import Point
import ctypes
import json
import re

#%%

def _screen_resolution():
    '''computes server screen resolution'''
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))
    
    return width,height

def _update_map_select_src(location_id,gdf=None):
    if debug: print('bokeh: _update_map_select_src')
    if gdf is None:
        gdf = gpd.GeoDataFrame.from_features(json.loads(map_src.geojson)['features'])
        gdf.index = gdf['locationId']
    x = list(gdf[gdf['locationId'].isin(location_id)]['geometry'].x.values)
    y = list(gdf[gdf['locationId'].isin(location_id)]['geometry'].y.values)
    #x,y = [gdf.loc[location_id]['geometry'].x,gdf.loc[location_id]['geometry'].y]
    map_select_src.data.update({'x':x,'y':y})
    #map_select_src.data.update({'x':[x],'y':[y]})
    
    return x,y       

def _update_time_fig(location_id,parameter_id):
    if debug: print('bokeh: _update_time_fig')
    if (len(location_id) > 0) and (len(parameter_id) > 0):
        
        df = rest.get_timeseries(filterId = filter_children[select_filter.value],
                                  locationIds = location_id[0],
                                  parameterIds = parameter_id[0],
                                  startTime = start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                  endTime = end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                  thinning = thinner)

        if not df is None:
            try:
                start = pd.Timestamp.now()
    
                src = ColumnDataSource(data=df)
                time_src.data.update(src.data)
                time_fig.title.text = df.location_id
                time_fig.yaxis.axis_label = f'{df.parameter_id} [{df.units}]'
                time_fig.xaxis.axis_label = 'datum [gmt {0:+}]'.format(int(float(df.time_zone)))
               
                
                try:
                    time_x_range.start = df["datetime"].min()
                    time_x_range.end = df["datetime"].max()
                except:
                    print(f'x-range:{df["datetime"].min()} - {df["datetime"].max()}')
                    time_x_range.start = rest.start_time
                    time_x_range.end = rest.end_time
                try:
                    time_y_range.start = df["value"].min()
                    time_y_range.end = df["value"].max()
                except:
                    print(f'y-range:{df["value"].min()} - {df["value"].max()}')
                    time_y_range.start = 0
                    time_y_range.end = 1
                    
                tabs.active = 1 
    
                delta = pd.Timestamp.now() - start
                print(f'plot graph in {delta.seconds + delta.microseconds/1000000} seconds, {len(df["value"])} timesteps')
            except:
                print(f'bokeh failed to plot response from server-url: {df.url}')
    else:
        time_src.data.update({'datetime':[],'value':[]})

def update_on_tap(event):
    if debug: print('bokeh: _update_on_tap')
    '''update time_graph with location selected'''
    x, y = event.__dict__['x'],event.__dict__['y']
    distance_threshold = (map_x_range.end - map_x_range.start) * 0.005
    gdf = gpd.GeoDataFrame.from_features(json.loads(map_src.geojson)['features'])
    gdf['distance'] = gdf['geometry'].distance(Point(x,y))
    gdf = gdf.loc[gdf['distance'] < distance_threshold]
    if not gdf.empty:
        gdf.index = gdf['locationId'] 
        locations = list(gdf.sort_values('distance').index)
        
        _update_map_select_src(locations,gdf)
        
        select_locations.value = locations

        _update_time_fig(location_id=select_locations.value,
                         parameter_id=select_parameters.value)   

width,height = _screen_resolution()

def update_on_filter_select(attrname, old, new):
    if debug: print('bokeh: _update_on_filter_select')
    select_value = select_filter.value
    
    gdf = rest.get_locations(filterId=filter_children[select_value])
    map_src.geojson = gdf.to_json()   
    locations = list(gdf['locationId'].values)
    select_locations.options = locations
    select_locations.value = [val for val in select_locations.value if val in locations]
    
    parameters = rest.get_parameters(filter_selected=filter_children[select_value])
    select_parameters.options = parameters
    select_parameters.value = [val for val in select_parameters.value if val in parameters]
    
    if (not select_locations.value) or (not select_parameters.value):
        tabs.active = 0
        time_src.data.update({'datetime':[],'value':[]})
    
def update_on_locations_select(attrname, old, new):
    if debug: print('bokeh: _update_on_locations_select')
    _update_map_select_src(select_locations.value)
       
    if select_locations.value:
        parameters = rest.get_parameters(filter_selected=filter_children[select_filter.value],
                                         locations = select_locations.value)
        select_parameters.options = parameters
        select_parameters.value = [val for val in select_parameters.value if val in parameters]
        
        _update_time_fig(location_id=select_locations.value,
                     parameter_id=select_parameters.value)
        
       
def update_on_parameters_select(attrname, old, new):
    if debug: print('bokeh: _update_on_parameters_select')
    
    _update_time_fig(location_id=select_locations.value,
                     parameter_id=select_parameters.value)  

#%% pi-rest object
rest = fews_rest.pi_rest(url,start_time,end_time)

#%% time fig widget
time_src = ColumnDataSource(data={'datetime':[],'value':[]})

timespan = (end_time - start_time).days
thinner = int(timespan * 86400 * 1000 / width)
print(f'thinner {thinner}')

time_x_range = Range1d(start=start_time, end=end_time, bounds=None)
time_y_range = Range1d(start=0, end=1, bounds=None)

time_hover =    HoverTool(tooltips=[('datetime', '@datetime{%F}'),
                                    ('value', '@value')],
                          formatters={'@datetime': 'datetime'})

time_fig = figure(title = '',
                  tools=['pan','box_zoom','wheel_zoom','reset',time_hover,'save'],
                  active_drag=None,
                  height = int(height *0.75),
                  width = int(width * 0.75),
                  y_axis_label = ' []',
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

#%% map fig widget
map_gdf = rest.get_locations(filterId=filter_selected)
map_src = GeoJSONDataSource(geojson=map_gdf.to_json())
map_select_src = ColumnDataSource({'x':[],'y':[]})

xmin,ymin,xmax,ymax = map_gdf['geometry'].buffer(map_buffer).total_bounds
map_x_range = Range1d(start=xmin, end=xmax, bounds=None)
map_y_range = Range1d(start=ymin, end=ymax, bounds=None)

map_hover = HoverTool(tooltips = [ ('locationId', '@locationId'),
                                  ('shortName', '@shortName')])


map_fig = figure(tools=['wheel_zoom','pan',map_hover], 
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
               source=map_src, 
               line_color="blue", 
               fill_color="white", 
               line_width=2)

map_fig.circle('x', 'y', 
               size=3, 
               source=map_select_src, 
               line_color="red", 
               fill_color="red")

map_fig.on_event(events.Tap, update_on_tap)

#%% filter selection widget
filters = rest.get_filters(filterId=filter_parent)
filter_children =  {item['name']:item['id'] for item in filters[filter_parent]['child']}
filter_value = next(key for key,value in filter_children.items() if value == filter_selected)
select_filter = Select(title="Filters:", value=filter_value, options=list(filter_children.keys()))

select_filter.on_change('value', update_on_filter_select)

#%% location selection widget
locations = list(map_gdf['locationId'].values)
select_locations = MultiSelect(title="Locations:", value=[], options=locations)
select_locations.height = int(height * 0.25)

select_locations.on_change('value', update_on_locations_select)

#%% parameter selection widget
select_parameters = MultiSelect(title="Parameters:", value=[], options=[])
select_parameters.height = int(height * 0.25)
select_parameters.options = rest.get_parameters(filter_selected=filter_selected)

select_parameters.on_change('value', update_on_parameters_select)

#%% layout
tabs = Tabs(tabs=[Panel(child=map_fig, title="kaart"),
                  Panel(child=time_fig, title="grafiek")]
            )

layout = row(column(select_filter,select_locations,select_parameters),
             tabs)

curdoc().add_root(layout)
curdoc().title = title