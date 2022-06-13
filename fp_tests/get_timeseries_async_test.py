from datetime import datetime
from config import api, get_time_series_async

LOCATION_IDS = ['NL34.HL.KGM154.LWZ1',
                'NL34.HL.KGM154.HWZ1',
                'NL34.HL.KGM154.KWK',
                'NL34.HL.KGM156.PMP2',
                'NL34.HL.KGM156.HWZ1',
                'NL34.HL.KGM155.HWZ1',
                'NL34.HL.KGM156.KSL1',
                'NL34.HL.KGM156.LWZ1',
                'NL34.HL.KGM156.PMP1',
                'NL34.HL.KGM154.PMP1',
                'NL34.HL.KGM155.LWZ1']
PARAMETER_IDS = ["Q [m3/s] [NVT] [OW]", "WATHTE [m] [NAP] [OW]"]

timeseriesset = get_time_series_async(url="https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1/timeseries",
                                      filter_id="WDB_OW_KGM",
                                      location_ids=LOCATION_IDS,
                                      start_time=datetime(2022, 5, 1),
                                      end_time=datetime(2022, 5, 5),
                                      parameter_ids=PARAMETER_IDS,
                                      parallel=True)

print(timeseriesset)
def test_time_zone():
    assert timeseriesset.time_zone == 1.0


def test_version():
    assert timeseriesset.version == "1.28"


def test_empty():
    assert not timeseriesset.empty


def test_length():
    assert len(timeseriesset) == 11


def test_parameter_ids():
    assert all([i in PARAMETER_IDS
                for i in timeseriesset.parameter_ids])


def test_location_ids():
    assert all([i in LOCATION_IDS
                for i in timeseriesset.location_ids])


def test_qualifier_ids():
    assert timeseriesset.qualifier_ids == ['validatie']
