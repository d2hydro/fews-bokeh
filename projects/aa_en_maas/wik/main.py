# -*- coding: utf-8 -*-
"""
Created on Tue Dec  1 13:13:25 2020

@author: danie
"""

from config import title, url, thinner, map_buffer, start_time, end_time, filter_parent, filter_selected, parameter_filter, debug
from fewsbokeh.sources import fews_rest
from fewsbokeh import map_figure, time_figure
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
import logging
from itertools import cycle

from bokeh import events
from bokeh.io import curdoc, show
from bokeh.models.widgets import Select,Div,Panel,Tabs,MultiSelect
from bokeh.models import ColumnDataSource,GeoJSONDataSource,DatetimeTickFormatter,Tool,Range1d,HoverTool
from bokeh.core.properties import String
from bokeh.layouts import row,column
from bokeh.palettes import Category10_10 as palette
from bokeh.plotting import figure
from bokeh.tile_providers import get_provider, Vendors
from shapely.geometry import Point
import ctypes
import json
import re

#%%

_UNITS_MAPPING = dict(nonequidistant='noneq',
                      second='sec')

def _screen_resolution():
    '''computes server screen resolution'''
    width = int(ctypes.windll.user32.GetSystemMetrics(0))
    height = int(ctypes.windll.user32.GetSystemMetrics(1))
    
    return width,height

def _update_map_select_src(location_id):
    x = rest.locations.loc[location_id]['geometry'].x.to_list()
    y = rest.locations.loc[location_id]['geometry'].y.to_list()
    loc_select_src.data = {'x':x,'y':y}

def _update_time_fig(location_id,parameter_id):
    if debug: print('bokeh: _update_time_fig')
    colors = cycle(palette)
    if (len(location_id) > 0) and (len(parameter_id) > 0):
        
        title = ','.join(_to_location_names(location_id))
        #add all children
        location_id += rest.locations[rest.locations['parentLocationId'].isin(location_id)]['parentLocationId'].index.to_list()
        
        #get all time_series   
        time_zone, time_series = rest.get_timeseries(filterId = filter_children[select_filter.value],
                                                     locationIds = location_id,
                                                     parameterIds = parameter_id,
                                                     startTime = start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                                     endTime = end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                                     thinning = thinner)
        parameter_groups = rest.parameters.loc[parameter_id]['parameterGroup'].to_list()
        line_glymphs = {group:[] for group in parameter_groups}
        y_ranges = {group:{'ymin':[],'ymax':[]} for group in parameter_groups}
        
        
        #make a color-scheme
        color_df = pd.DataFrame([dict(location=ts['header']['locationId'],
                                      parameter=ts['header']['parameterId'],
                                      ts_unit=ts['header']['timeStep']['unit'],
                                      group=rest.parameters.loc[ts['header']['parameterId']]['parameterGroup']) 
                                 for ts in time_series])
        color_df.sort_values(by=['group','parameter','ts_unit', 'location'], inplace=True)
        color_df.set_index(['group','location','parameter','ts_unit'], inplace=True)
        color_df['color'] = None
        grouper = color_df.groupby('group')
        for _,df in grouper:
            colors = cycle(palette)
            for idx, row in df.iterrows():
                color_df.loc[idx, 'color'] = next(colors)
        
        x_min = []
        x_max = []
        for ts in time_series:
            if 'events' in ts.keys():
                header = ts['header']
                group = rest.parameters.loc[header['parameterId']]['parameterGroup']
                location = header['locationId']
                parameter = header['parameterId']
                ts_unit = header['timeStep']['unit']
                color = color_df.loc[group,location,parameter,ts_unit]['color']
                line_glymphs[group] += [{'type':'line',
                                        'color':color,
                                        'source':ColumnDataSource(ts['events']),
                                        'legend_label':f'{rest.locations.loc[header["locationId"]]["shortName"]} {rest.parameters.loc[header["parameterId"]]["name"]} [{_UNITS_MAPPING[header["timeStep"]["unit"]]}]'}]
                if not ts['events'].empty:
                    x_min += [ts['events']['datetime'].min()]
                    x_max += [ts['events']['datetime'].max()]
                    y_ranges[group]['ymin'] += [ts['events']['value'].min()]
                    y_ranges[group]['ymax'] += [ts['events']['value'].max()]         
        
        
        x_axis_label = 'datum-tijd [gmt {0:+}]'.format(int(float(time_zone)))

        if len(x_min) > 0:
            x_min = min(x_min)
        else: x_min = start_time
        
        if len(x_max) > 0:
            x_max = max(x_max)
        else:
            x_max = end_time
        
        time_x_range = Range1d(start=x_min, end=x_max, bounds='auto')
        time_x_range.start = x_min
        time_x_range.end = x_max
        
        if len(tabs.tabs) == 2:
            tabs.tabs.remove(tabs.tabs[1])
        
        fig_height = int(height *0.75/len(line_glymphs))
        time_figs = []
        for idx, (key, values) in enumerate(line_glymphs.items()):
            if len(y_ranges[key]['ymin']) > 0:
                y_min = min(y_ranges[key]['ymin'])
            else: y_min = 0
        
            if len(y_ranges[key]['ymax']) > 0:
                y_max = max(y_ranges[key]['ymax'])
            else:
                y_max = 1
                
            time_y_range = Range1d(start=y_min, end=y_max, bounds=(y_min-1,y_max+1))
            
            if idx == 0:
                fig_title = title
            else:
                fig_title = ''
            
            if len(parameter_id) == 1:
                y_axis_label = rest.parameters.loc[parameter_id[0]]['name']
            else:
                unit = rest.parameters.loc[rest.parameters['parameterGroup'] == key]['displayUnit'].to_list()[0]
                y_axis_label = f'{key} [{unit}]'
                
            if idx == len(line_glymphs)-1:
                x_axis_visible = True
            else:
                x_axis_visible = False
            
            time_figs += [time_figure.generate(title=fig_title,
                                                width=int(width * 0.75),
                                                height=fig_height,
                                                x_axis_label=x_axis_label,
                                                y_axis_label=y_axis_label,
                                                x_axis_visible=x_axis_visible,
                                                x_range=time_x_range,
                                                y_range=time_y_range,
                                                glymphs=values)]
        
        tabs.tabs.append(Panel(child=column(*time_figs), title="grafiek", name='grafiek'))
            
        tabs.active = 1
        
def _to_location_names(location_ids):
    ''' returns the location names from a list of parameter_ids '''
    if isinstance(location_ids,list):
        return rest.locations.loc[rest.locations['locationId'].isin(location_ids)]['shortName'].to_list()
    else:
        return rest.locations.loc[rest.locations['locationId'] == location_ids]['shortName']

def _to_location_ids(location_names):
    ''' returns the location names from a list of parameter_ids '''
    if isinstance(location_names,list):
        return rest.locations.loc[rest.locations['shortName'].isin(location_names)]['locationId'].to_list()
    else:
        return rest.locations.loc[rest.locations['shortName'] == location_names]['locationId']

def get_loc_df(filter_id):
    ''' get loc_df as input for map source'''
    gdf = rest.get_locations(filterId=filter_id)
    bounds = gdf['geometry'].buffer(map_buffer).total_bounds
    df = pd.DataFrame(gdf.drop(['geometry'],axis=1))
    df = df.loc[df['parentLocationId'].isna()]
    df['type'] = 'overig'
    df.loc[df['locationId'].str.match('[A-Z]{3}-[A-Z]{3}-[A-Z]{3}'), 'type'] = 'neerslag'
    df.reset_index(drop=True,inplace=True)
    
    return bounds, df
    

def update_on_double_tap(event):
    if debug: print('bokeh: update_on_tap')
    '''update time_graph with location selected'''
   
    _update_map_select_src([])
    
    select_locations.value = []
        
def update_on_tap(event):
    if debug: print('bokeh: update_on_tap')
    '''update time_graph with location selected'''
    x, y = event.__dict__['x'],event.__dict__['y']
    distance_threshold = (map_x_range.end - map_x_range.start) * 0.005
    gdf = rest.locations.copy()
    gdf['distance'] = gdf['geometry'].distance(Point(x,y))
    gdf = gdf.loc[gdf['distance'] < distance_threshold]
    if not gdf.empty:
        gdf.index = gdf['locationId'] 
        locations = _to_location_ids(select_locations.value) + gdf.sort_values('distance').index.to_list()
        _update_map_select_src(locations)
        
        select_locations.value = _to_location_names(locations)

        _update_time_fig(location_id=select_locations.value,
                         parameter_id=rest.to_parameter_ids(select_parameters.value))  


def update_on_filter_select(attrname, old, new):
    if debug: print('bokeh: update_on_filter_select')
    select_value = select_filter.value
    
    _,loc_df = get_loc_df(filter_children[select_value])
    
    loc_src_pluvial.data.update(ColumnDataSource('x', 'y',data=loc_df.loc[loc_df['type'] == 'neerslag']).data)
    loc_src_other.data.update(ColumnDataSource('x', 'y',data=loc_df.loc[loc_df['type'] == 'overig']).data)
    
    select_locations.options = loc_df['shortName'].to_list()
    select_locations.value = [val for val in select_locations.value if val in locations]
    
    parameters = rest.get_parameters(filter_selected=filter_children[select_value])
    select_parameters.options = rest.parameters.loc[parameters]['name'].to_list()
    select_parameters.value = [val for val in select_parameters.value if val in parameters]
    
    if (not select_locations.value) or (not select_parameters.value):
        tabs.active = 0
        time_src.data.update({'datetime':[],'value':[]})
    
def update_on_locations_select(attrname, old, new):
    if debug: print('bokeh: update_on_locations_select')
    _update_map_select_src(_to_location_ids(select_locations.value))
       
    if select_locations.value:
        parameters = rest.get_parameters(filter_selected=filter_children[select_filter.value],
                                         locations = _to_location_ids(select_locations.value))
        select_parameters.options = rest.parameters.loc[parameters]['name'].to_list()
        select_parameters.value = [val for val in select_parameters.value if val in parameters]
        
        _update_time_fig(location_id=_to_location_ids(select_locations.value),
                     parameter_id=rest.to_parameter_ids(select_parameters.value))
        
       
def update_on_parameters_select(attrname, old, new):
    if debug: print('bokeh: update_on_parameters_select')
    
    _update_time_fig(location_id=_to_location_ids(select_locations.value),
                     parameter_id=rest.to_parameter_ids(select_parameters.value))

#%% create logger
if not 'logger' in locals().keys():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)

#%% pi-rest object
rest = fews_rest.api(url, logger)

width,height = _screen_resolution()

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

time_glymps = [{'type':'line', 'color': 'blue', 'source': time_src, 'legend_label':''}]


time_fig = time_figure.generate(width=int(width * 0.75),
                                height=int(height *0.75),
                                x_range=time_x_range,
                                y_range=time_y_range,
                                glymphs=time_glymps)

#%% map fig widget
bounds, loc_df = get_loc_df(filter_selected)
loc_src_pluvial = ColumnDataSource('x', 'y',data=loc_df.loc[loc_df['type'] == 'neerslag'])
loc_src_other = ColumnDataSource('x', 'y',data=loc_df.loc[loc_df['type'] == 'overig'])
loc_select_df = pd.DataFrame({'x':[],'y':[]})
loc_select_src = ColumnDataSource('x', 'y',data=loc_select_df)

map_x_range = Range1d(start=bounds[0], end=bounds[2], bounds=None)
map_y_range = Range1d(start=bounds[1], end=bounds[3], bounds=None)

map_glymphs = [{'type': 'inverted_triangle',
                'size': 5,
                'source': loc_src_pluvial,
                'line_color': 'blue',
                'fill_color': 'white',
                'line_width': 1,
                'legend_label': 'neerslag'},
               {'type': 'inverted_triangle',
                'size': 5,
                'source': loc_src_other,
                'line_color': 'orange',
                'fill_color': 'white',
                'line_width': 1,
                'legend_label': 'overig'},
                {'type': 'circle',
                 'size': 4,
                 'source': loc_select_src,
                 'fill_color': 'red'}]

map_fig = map_figure.generate(width=int(width * 0.75),
                              height=int(height *0.75),
                              x_range=map_x_range,
                              y_range=map_y_range,
                              glymphs=map_glymphs
                              )

#map_fig.circle(source=loc_src_pluvial)
#show(map_fig)

map_fig.on_event(events.Tap, update_on_tap)

map_fig.on_event(events.DoubleTap, update_on_double_tap)

#%% filter selection widget
filters = rest.get_filters(filterId=filter_parent)
filter_children =  {item['name']:item['id'] for item in filters[filter_parent]['child']}
filter_value = next(key for key,value in filter_children.items() if value == filter_selected)
select_filter = Select(title="Filters:", value=filter_value, options=list(filter_children.keys()))

select_filter.on_change('value', update_on_filter_select)

#%% location selection widget
locations = loc_df['shortName'].to_list()
select_locations = MultiSelect(title="Locations:", value=[], options=locations)
select_locations.height = int(height * 0.25)

select_locations.on_change('value', update_on_locations_select)

#%% parameter selection widget
select_parameters = MultiSelect(title="Parameters:", value=[], options=[])
select_parameters.height = int(height * 0.25)

select_parameters.options = rest.to_parameter_names(rest.get_parameters(filter_selected=filter_selected))

select_parameters.on_change('value', update_on_parameters_select)

#%% layout
map_panel = Panel(child=map_fig, title="kaart", name='kaart')
time_panel = Panel(child=time_fig, title="grafiek", name='grafiek')
tabs = Tabs(tabs=[map_panel,
                  time_panel]
            )

layout = row(column(select_filter,select_locations,select_parameters),
             tabs)

curdoc().add_root(layout)
curdoc().title = title