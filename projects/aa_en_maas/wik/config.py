# -*- coding: utf-8 -*-
"""
Created on Thu Dec  3 17:07:46 2020

@author: danie
"""
import pandas as pd

title = 'Bokeh FEWS-REST client op WIK Aa en Maas'
url =  'http://localhost:7080/FewsWebServices/rest/fewspiservice/v1/'
thinner = None
map_buffer = 1000
start_time = pd.Timestamp(year=2019,month=1,day=1)
end_time = pd.Timestamp.now()
filter_parent = 'Export_Hydronet'
filter_selected = 'Hydronet_Keten'
parameter_filter = '.*'
debug = True