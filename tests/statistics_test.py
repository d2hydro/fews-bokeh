import sys
from pathlib import Path
import pandas as pd

parentdir = Path(__file__).parents[1]
sys.path.insert(0, parentdir.as_posix())


from utils.statistics import (
    cumulative,
    average,
    median,
    quantile_90,
    quantile_10,
    maximum,
    minimum
    )

data_dir = Path("../data")
df = pd.read_csv(data_dir / "test_data.csv")


def test_cumulative():
    assert True
