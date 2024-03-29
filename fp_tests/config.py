import sys
from pathlib import Path
parentdir = Path(__file__).parents[1]
sys.path.insert(0, parentdir.as_posix())

from fewspy.api import Api
from fewspy.get_time_series_async import get_time_series_async

api = Api(
    url="https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1/"
    )
