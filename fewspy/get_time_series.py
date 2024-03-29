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


def _ts_or_headers(only_headers=False):
    if only_headers:
        return "Headers {status}"
    else:
        return "TimeSeries {status}"


def get_time_series(
        url: str,
        filter_id: str,
        location_ids: Union[str, List[str]] = None,
        parameter_ids: Union[str, List[str]] = None,
        qualifier_ids: Union[str, List[str]] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        thinning: int = None,
        only_headers: bool = False,
        show_statistics: bool = False,
        document_format: str = "PI_JSON",
        parallel: bool = False,
        verify: bool = False,
        logger=LOGGER
        ) -> pd.DataFrame:
    """
    Get FEWS qualifiers as a pandas DataFrame

    Args:
        url (str): url Delft-FEWS PI REST WebService.
        E.g. http://localhost:8080/FewsWebServices/rest/fewspiservice/v1/qualifiers
        verify (bool, optional): passed to requests.get verify parameter.
        Defaults to False.
        logger (logging.Logger, optional): Logger to pass logging to. By
        default a logger will ge created.

    Returns:
        df (pandas.DataFrame): Pandas dataframe with index "id" and columns
        "name" and "group_id".

    """
    report_string = _ts_or_headers(only_headers)

    # do the request
    timer = Timer(logger)
    parameters = parameters_to_fews(locals())
    print("parameters=",parameters)
    
    if (parallel==False):
        response = requests.get(url, parameters, verify=verify)
        timer.report(report_string.format(status="request"))
    
        # parse the response
 
        if response.status_code == 200:
            pi_time_series = response.json()
            time_series_set = TimeSeriesSet.from_pi_time_series(pi_time_series)
            timer.report(report_string.format(status="parsed"))
        else:
            logger.error(f"FEWS Server responds {response.text}")
            time_series_set = TimeSeriesSet()

   
           
        time_series_set = result_async
        print(time_series_set)

    return time_series_set
