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


FILTER_RELATIONS = {"WIK_KET_Rioolgemaal": ["RIOLERINGSDISTRICT"]}

filter_id = "Hydronet_Gemert-Bakel"
data.update_filter_select([filter_id])

location_ids = ['HMD0220', "HMD0202A003","HMD0202A001"]
parameter_ids = ['H.meting']

data.create_timeseries(location_ids, parameter_ids)

location_id = ["HMD0202A003"]
result = data.timeseries.get_lr_data(
            data.filters.selected["id"],
            location_id,
            parameter_ids,
            start_datetime=data.timeseries.search_start_datetime ,
            end_datetime=data.timeseries.search_end_datetime,
        )

def flatten_relations(x, relations):
    return [i["relatedLocationId"] for i in x["relations"] if i["id"] in relations]

def test_fews_get_filters_relations():
    filter_id = "WIK_KET_Rioolgemaal"
    includeLocationRelations = True
    gdf = data.fews_api.get_locations(filterId=filter_id,
                                      includeLocationRelations=includeLocationRelations)

    return gdf


def test_data_fetch_relations(filter_id = "WIK_KET_Rioolgemaal"):
    """Test of related locations goed worden weggegooid."""
    tuple_values = data.filters.get_tuples([filter_id])
    data.locations.fetch(tuple_values)
    
    return "BER-HEE-KER" not in data.locations.df["locationId"]
    
def test_data_fetch_non_relations(filter_id = "WIK_KET_Neerslag"):
    """Test of het zonder related locations nog werkt."""
    tuple_values = data.filters.get_tuples([filter_id])
    data.locations.fetch(tuple_values)
    
def test_tuple_values():
    values = ['WIK_KET_Rioolgemaal']
    return data.filters.get_tuples(values)

