# -*- coding: utf-8 -*-

# import os-modules

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests

_geodatum = {'WGS 1984':'epsg:4326',
             'Rijks Driehoekstelsel':'epsg:28992'}

   
def get_locations(url,documentFormat='PI_JSON',showAttributes=False,filterId=None,documentVersion='1.26'):
    rest_url = f'{url}locations'
    
    parameters = dict(documentFormat=documentFormat,
                      showAttributes=showAttributes,
                      filterId=filterId,
                      documentVersion=documentVersion)
    
    response = requests.get(rest_url,parameters)
    if response.status_code == 200:
        gdf = gpd.GeoDataFrame(response.json()['locations'])
        gdf['geometry'] = gdf.apply((lambda x:Point(float(x['x']),float(x['y']))),axis=1)
        gdf.crs = _geodatum[response.json()['geoDatum']]
        gdf = gdf.to_crs('epsg:3857')
        gdf['x'] = gdf['geometry'].x
        gdf['y'] = gdf['geometry'].y
        drop_cols = [col for col in gdf.columns if not col in ['locationId', 'description', 'shortName', 'geometry']]
        gdf = gdf.drop(drop_cols,axis=1)
        
    return gdf

def get_timeseries(url,locationIds,parameterIds,startTime,endTime,documentFormat='PI_JSON',documentVersion='1.23',thinning=None,onlyHeaders=False):
    start = pd.Timestamp.now()
    rest_url = f'{url}timeseries'
    
    parameters = dict(locationIds=locationIds,
                      parameterIds=parameterIds,
                      startTime=startTime,
                      endTime=endTime,
                      documentFormat=documentFormat,
                      documentVersion=documentVersion,
                      onlyHeaders=onlyHeaders,
                      thinning=thinning)
    
    response = requests.get(rest_url,parameters)
    
    delta = pd.Timestamp.now() - start
    print(f'get timeseries in {delta.seconds + delta.microseconds/1000000}')
    
    if response.status_code == 200:
        if onlyHeaders:
            return response.json()
        
        elif 'timeSeries' in response.json().keys():
            time_series = response.json()['timeSeries'][0]
            if 'events' in time_series.keys():
                df = pd.DataFrame(time_series['events'])
                df['datetime'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['time'])
                df['value'] = pd.to_numeric(df['value'])
                df.parameter = time_series['header']['parameterId']
                df.units = time_series['header']['units']
                df.location = time_series['header']['locationId']
                df.time_zone = response.json()['timeZone']
            
                return df
        
        else:
            print(response.json())
            
            return None
        
    