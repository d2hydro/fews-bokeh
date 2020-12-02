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
from bokeh.models.widgets import Select,Div,Panel,Tabs,MultiSelect
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
filter_parent = 'Fluvial'
filter_selected = 'HW_WVS'

#%%

def _screen_resolution():
    '''computes server screen resolution'''
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))
    
    return width,height

def _update_map_select_src(location_id,gdf=None):
    if gdf is None:
        gdf = gpd.GeoDataFrame.from_features(json.loads(map_src.geojson)['features'])
        gdf.index = gdf['locationId']
    x,y = [gdf.loc[location_id]['geometry'].x,gdf.loc[location_id]['geometry'].y]
    map_select_src.data.update({'x':[x],'y':[y]})
    

def _update_map_time_fig(location_id):
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

def update_plot_on_tap(event):
    '''update time_graph with location selected'''
    x, y = event.__dict__['x'],event.__dict__['y']
    distance_threshold = (map_x_range.end - map_x_range.start) * 0.05
    gdf = gpd.GeoDataFrame.from_features(json.loads(map_src.geojson)['features'])
    gdf['distance'] = gdf['geometry'].distance(Point(x,y))
    gdf = gdf.loc[gdf['distance'] < distance_threshold]
    if not gdf.empty:
        gdf.index = gdf['locationId'] 
        location_id = gdf.sort_values('distance').index[0]
        
        _update_map_select_src(location_id,gdf)
        
        select_locations.value = [location_id]

        _update_map_time_fig(location_id)  

width,height = _screen_resolution()

def update_locations_on_filter_select(attrname, old, new):
    select_value = select_filter.value
    
    gdf = fews_rest.get_locations(url,filterId=filter_children[select_value])
    map_src.geojson = gdf.to_json()
    
    locations = list(gdf['locationId'].values)
    select_locations.options = locations
    select_locations.value = []
    
def update_map_select_on_locations_select(attrname, old, new):
    location_id = select_locations.value[0]
    
    _update_map_time_fig(location_id)
    _update_map_select_src(location_id)
    

#%% time fig widget
time_df = pd.DataFrame({'datetime':[],'value':[]})
time_df.location = ''
time_df.time_zone = '0'
time_df.parameter = ''
time_df.units = ''

time_src = ColumnDataSource(data=time_df)

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

#%% map fig widget
map_gdf = fews_rest.get_locations(url,filterId=filter_selected)
map_src = GeoJSONDataSource(geojson=map_gdf.to_json())
map_select_src = ColumnDataSource({'x':[],'y':[]})

xmin,ymin,xmax,ymax = map_gdf['geometry'].buffer(map_buffer).total_bounds
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
               source=map_src, 
               line_color="blue", 
               fill_color="white", 
               line_width=2)

map_fig.circle('x', 'y', 
               size=3, 
               source=map_select_src, 
               line_color="red", 
               fill_color="red")

map_fig.on_event(events.Tap, update_plot_on_tap)

#%% filter selection widget
filters = fews_rest.get_filters(url,filterId=filter_parent)
filter_children =  {item['name']:item['id'] for item in filters[filter_parent]['child']}
filter_value = next(key for key,value in filter_children.items() if value == filter_selected)
select_filter = Select(title="Filters:", value=filter_value, options=list(filter_children.keys()))

select_filter.on_change('value', update_locations_on_filter_select)

#%% location selection widget
locations = list(map_gdf['locationId'].values)
select_locations = MultiSelect(title="Locations:", value=[], options=locations)
select_locations.height = int(height * 0.25)

select_locations.on_change('value', update_map_select_on_locations_select)

#%% layout
tabs = Tabs(tabs=[Panel(child=map_fig, title="kaart"),
                  Panel(child=time_fig, title="grafiek")]
            )

layout = row(column(select_filter,select_locations),
             tabs)

curdoc().add_root(layout)
curdoc().title = 'Bokeh FEWS-REST client'