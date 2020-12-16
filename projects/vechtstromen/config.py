# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import pandas as pd

url =  'https://fewsvechtdb.lizard.net/FewsWebServices/rest/fewspiservice/v1/'
thinner = None
map_buffer = 1000
start_time = pd.Timestamp(year=2020,month=1,day=1)
end_time = pd.Timestamp.now()
filter_parent = 'Fluvial'
filter_selected = 'HW_WVS'
parameter_filter = '.*meetwaarde'