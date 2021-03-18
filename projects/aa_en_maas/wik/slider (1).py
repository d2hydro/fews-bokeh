# -*- coding: utf-8 -*-
"""
Created on Mon Mar  8 09:34:04 2021

@author: danie
"""


from bokeh.models.widgets import DateRangeSlider
import pandas as pd
from bokeh.io import curdoc


# %%
def update_on_search_period(attrname, old, new):
    start_datetime = pd.Timestamp(new[0] * 1000000)
    end_datetime = pd.Timestamp(new[1] * 1000000)

    days = (end_datetime - start_datetime).days
    if days > 150:
        if old[0] != new[0]:
            search_period_slider.value = (start_datetime, start_datetime + pd.Timedelta(days=150))
        elif old[1] != new[1]:
            search_period_slider.value = (end_datetime - pd.Timedelta(days=150), end_datetime)


search_period_slider = DateRangeSlider(value=(pd.Timestamp("2000-12-01"), pd.Timestamp("2001-01-01")),
                                       start=pd.Timestamp("2000-01-01"),
                                       end=pd.Timestamp("2002-01-01"),
                                       title="Zoekperiode")

search_period_slider.on_change("value", update_on_search_period)

curdoc().add_root(search_period_slider)
