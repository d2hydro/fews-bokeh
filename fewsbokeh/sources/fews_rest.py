# -*- coding: utf-8 -*-

# import os-modules

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests

_GEODATUM = {'WGS 1984':'epsg:4326',
             'Rijks Driehoekstelsel':'epsg:28992'}

_REQUEST_PARAMETERS_ALLOWED = {'timeseries':['locationIds',
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
            par_df = pd.DataFrame(response.json()['timeSeriesParameters']).set_index('id')
            return par_df
        else:
            return None

class api():
    
    def __init__(self, url, logger):
        self.document_format='PI_JSON'
        self.url = url
        self.parameters = _get_parameters(url)
        self.locations = None
        self.logger = logger
        
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
                                         parameterIds = self.parameters.index.to_list(),
                                         onlyHeaders = True)
        
        if 'timeSeries' in timeseries.keys():
            result = list(set([series['header']['parameterId'] 
                             for series in timeseries['timeSeries']]))

        else:
            print(f'no timeSeries in filter {filter_selected} for locations {locations}')
        
        return result
    
    def to_parameter_names(self, parameter_ids):
        ''' returns the parameter names from a list of parameter_ids '''
        return self.parameters.loc[parameter_ids]['name'].to_list()
    
    def to_parameter_ids(self, parameter_names):
        ''' returns the parameter ids from a list of parameter_ids '''
        return self.parameters.loc[self.parameters['name'].isin(parameter_names)].index.to_list()
        
    def get_locations(self,showAttributes=False,filterId=None,documentVersion='1.26'):
        ''' request locations and return as GeoDataFrame '''
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
            drop_cols = [col for col in gdf.columns if not col in ['locationId', 
                                                                   'description', 
                                                                   'shortName', 
                                                                   'parentLocationId',
                                                                   'x',
                                                                   'y',
                                                                   'geometry']]
            gdf = gdf.drop(drop_cols,axis=1)
            gdf.index = gdf['locationId']
            
            self.locations = gdf
            
        return gdf
        
    def get_timeseries(self,filterId,locationIds=None,startTime=None,endTime=None,parameterIds=None,documentVersion=None,thinning=None,onlyHeaders=False,unreliables=False):
        start = pd.Timestamp.now()
        result = None
        rest_url = f'{self.url}timeseries'
          
        
        parameters = {key:value for key,value in locals().items() 
                      if value and (key in _REQUEST_PARAMETERS_ALLOWED['timeseries'])}
        
        parameters.update({'documentFormat':self.document_format})
                
        response = requests.get(rest_url,parameters)
        
        if response.status_code == 200:
            if onlyHeaders:
                delta = pd.Timestamp.now() - start 
                self.logger.info(f'get timeseries headers in {delta.seconds + delta.microseconds/1000000} seconds')
                return response.json()
            
            elif 'timeSeries' in response.json().keys():
                result = []
                for time_series in response.json()['timeSeries']:
                    ts = {}
                    if 'header' in time_series.keys():
                        ts['header'] = time_series['header']
                    if 'events' in time_series.keys():
                        df = pd.DataFrame(time_series['events'])
                        if not unreliables:
                            df = df.loc[pd.to_numeric(df['flag']) < 6]
                        df['datetime'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['time']) 
                        df['value'] = pd.to_numeric(df['value'])
                        df = df.loc[df['value'] != pd.to_numeric(ts['header']['missVal'])]
                        df = df.drop(columns=[col for col in df.columns if not col in ['datetime','value']])
                        ts['events'] = df   
                    result += [ts]                         
                
                delta = pd.Timestamp.now() - start        
                print(f'get timeseries in {delta.seconds + delta.microseconds/1000000} seconds')  
                
                return response.json()['timeZone'], result
            
            else:
                print(response.json())
                return response.json()
        
        else:
            print(f'server responded with error ({response.status_code}): {response.text}')
            print(f'url send to the server was: {response.url}')
        
        if result is None:
            print(response.url)
            
        return result
        
    