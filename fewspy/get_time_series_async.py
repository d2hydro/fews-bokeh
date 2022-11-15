# -*- coding: utf-8 -*-
"""
Created on Mon Jun 13 11:44:06 2022

@author: ngoor
"""
import requests
import pandas as pd
import logging
from .utils.timer import Timer
from .utils.transformations import parameters_to_fews
from typing import List, Union
from .time_series import TimeSeriesSet
from datetime import datetime
import aiohttp
import asyncio



LOGGER = logging.getLogger(__name__)

def get_time_series_async(
        url: str,
        filter_id: str,
        location_ids: Union[str, List[str]] = None,
        parameter_ids: Union[str, List[str]] = None,
        qualifier_ids: Union[str, List[str]] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        thinning: int = None,
   #     only_headers: bool = False,
   #     show_statistics: bool = False,
        document_format: str = "PI_JSON",
        parallel: bool = False,
        verify: bool = False,
        logger=LOGGER
        ) -> pd.DataFrame:
        
        parameters = parameters_to_fews(locals())

        def _get_loop():
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            finally:
                loop.set_debug(True)
                return loop  
            
        async def get_timeseries_async(location_id, parameter_id,session):
           """Get timerseries using FEWS (asynchronously)"""
           parameters["locationIds"] = [location_id]
           parameters["parameterIds"]= [parameter_id]
           print(parameters["qualifierIds"])
           parameters["qualifierIds"] = None
           try:
               response = await session.request(method='GET', url=url, params=parameters, verify_ssl=verify)
               print(response.url)
               response.raise_for_status()  
           except Exception as err:
               print(f"An error ocurred: {err}")
               response ={"notimeSeries":"1"}
           response_json = await response.json()
           return response_json

        async def run_program(location_id,parameter_id, session):
         
           """Wrapper for running program in an asynchronous manner"""
           try:
               response = await get_timeseries_async(location_id,parameter_id, session)
               print(f"{len(response.get('timeSeries'))}")
           except Exception as err:
               print(f"Exception occured: {err}")
               response ={"notimeSeries":"1"}
               pass
           return response
       
        async def asynciee():
           async with aiohttp.ClientSession(loop=loop) as session:
               print("fetching async")
               fetch_all = [run_program(location_id,parameter_id,session) for location_id in location_ids for parameter_id in parameter_ids]
               result_async = await asyncio.gather(*fetch_all)      
               return result_async           

        if __name__ == 'fewspy.get_time_series_async': 
            print("name=",__name__)
            loop = _get_loop()
            result_async =loop.run_until_complete(asynciee())
        timeseriesset = result_async
        return(timeseriesset)
   
