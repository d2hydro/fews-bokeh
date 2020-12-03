# -*- coding: utf-8 -*-

# import os-modules

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests

_GEODATUM = {'WGS 1984':'epsg:4326',
             'Rijks Driehoekstelsel':'epsg:28992'}

_PARAMETERS_ALLOWED = {'get_timeseries':['locationIds',
                                         'startTime',
                                         'endTime',
                                         'filterId',
                                         'parameterIds',
                                         'documentVersion',
                                         'thinning',
                                         'onlyHeaders']}

def _get_parameters(url,documentFormat='PI_JSON'):
    rest_url = f'{url}parameters'
    parameters = dict(documentFormat=documentFormat)    
    response = requests.get(rest_url,parameters)
    
    if response.status_code == 200:
        if 'timeSeriesParameters' in response.json().keys():
            return [item['id'] for item in response.json()['timeSeriesParameters']]
        else:
            return None

class pi_rest():
    
    def __init__(self, url, start_time, end_time):
        self.document_format='PI_JSON'
        self.url = url
        self.parameters = _get_parameters(url)
        self.start_time = start_time
        self.end_time = end_time

    def get_filters(self,filterId=None):
        rest_url = f'{self.url}filters'
        
        parameters = dict(documentFormat=self.document_format,
                          filterId=filterId)    
        
        response = requests.get(rest_url,parameters)
        
        if response.status_code == 200:
            if 'filters' in response.json().keys():
                filters = {item['id']:{key:value for key,value in item.items() if not key == 'id'} 
                           for item in response.json()['filters']}
                return filters
            else:
                return None
     
    def get_parameters(self,filter_selected,locations=None):
        result = None
        
        timeseries = self.get_timeseries(filterId = filter_selected,
                                         locationIds = locations,
                                         parameterIds = self.parameters,
                                         onlyHeaders = True)
        
        if 'timeSeries' in timeseries.keys():
            result = list(set([series['header']['parameterId'] 
                             for series in timeseries['timeSeries']]))

        else:
            print(f'no timeSeries in filter {filter_selected} for locations {locations}')
        
        return result
        
    def get_locations(self,showAttributes=False,filterId=None,documentVersion='1.26'):
        rest_url = f'{self.url}locations'
        
        parameters = dict(documentFormat=self.document_format,
                          showAttributes=showAttributes,
                          filterId=filterId,
                          documentVersion=documentVersion)
        
        response = requests.get(rest_url,parameters)
        if response.status_code == 200:
            gdf = gpd.GeoDataFrame(response.json()['locations'])
            gdf['geometry'] = gdf.apply((lambda x:Point(float(x['x']),float(x['y']))),axis=1)
            gdf.crs = _GEODATUM[response.json()['geoDatum']]
            gdf = gdf.to_crs('epsg:3857')
            gdf['x'] = gdf['geometry'].x
            gdf['y'] = gdf['geometry'].y
            drop_cols = [col for col in gdf.columns if not col in ['locationId', 'description', 'shortName', 'geometry']]
            gdf = gdf.drop(drop_cols,axis=1)
            
        return gdf
        
    def get_timeseries(self,filterId,locationIds=None,startTime=None,endTime=None,parameterIds=None,documentVersion=None,thinning=None,onlyHeaders=False,unreliables=False):
        start = pd.Timestamp.now()
        result = None
        rest_url = f'{self.url}timeseries'
               
        parameters = {key:value for key,value in locals().items() 
                      if value and (key in _PARAMETERS_ALLOWED['get_timeseries'])}
        
        parameters.update({'documentFormat':self.document_format})
                
        response = requests.get(rest_url,parameters)
        delta = pd.Timestamp.now() - start
        
        
        if response.status_code == 200:
            if onlyHeaders:
                print(f'get timeseries headers in {delta.seconds + delta.microseconds/1000000} seconds')
                return response.json()
            
            elif 'timeSeries' in response.json().keys():
                print(f'get timeseries in {delta.seconds + delta.microseconds/1000000} seconds')
                time_series = response.json()['timeSeries'][0]
                if 'events' in time_series.keys():
                    df = pd.DataFrame(time_series['events'])
                    if not unreliables:
                        df = df.loc[pd.to_numeric(df['flag']) < 6]
                    df['datetime'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['time'])
                    df['value'] = pd.to_numeric(df['value'])
                    df = df.drop(columns=[col for col in df.columns if not col in ['datetime','value']])
                    df.location_id = time_series['header']['locationId']
                    df.time_zone = response.json()['timeZone']
                    df.url = response.url
                
                    result = df
            
            else:
                print(response.json())
                result = response.json()
        
        else:
            print(f'server responded with error ({response.status_code}): {response.text}')
            print(f'url send to the server was: {response.url}')
            
        return result
        
    