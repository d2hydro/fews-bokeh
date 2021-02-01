# -*- coding: utf-8 -*-
"""
Created on Mon Feb  1 21:17:14 2021

@author: danie
"""

#%%
location_ids, parameter_ids, filter_id, parameter_groups = [['4120', 'OSS-HAR-HEU', 'MAA-VST-STA'],
                                                            ['H.meting', 'P.radar.cal', 'P.radar.cal.early', 'P.radar.cal.realtime', 'Q.meting.m3uur'],
                                                            "Hydronet_Keten",
                                                            ['Hoogte', 'Radar Neerslag', 'Radar Neerslag', 'Radar Neerslag', 'Debiet m3 per uur']]

data.timeseries.create(location_ids,
                   parameter_ids,
                   filter_id,
                   parameter_groups)