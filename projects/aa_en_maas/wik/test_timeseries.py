# -*- coding: utf-8 -*-
"""
Created on Fri Jun  4 09:50:11 2021

@author: danie
"""
import logging
from datamodel import Data

logger = logging.getLogger(__name__)
filter_id = "WIK_App"
data = Data(logger)

def test_empty_series():
    location_ids = ['RWZI_DINTHER'] 
    parameter_ids = ['Q.effluent.m3dag']
    parameter_groups = ["Debiet m3 per dag effluent"]
    data.timeseries.create(location_ids, parameter_ids, filter_id, parameter_groups)
    
    return data.timeseries.timeseries

def test_existing_series():
    location_ids = ['OSS-HAR-HEU'] 
    parameter_ids = ['P.radar.cal']
    parameter_groups = ['Radar Neerslag']
    data.timeseries.create(location_ids, parameter_ids, filter_id, parameter_groups)
    
    return data.timeseries.timeseries