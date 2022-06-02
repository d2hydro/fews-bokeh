from pathlib import Path
import pandas as pd

data_dir = Path("../data")

df = pd.read_csv(data_dir / "test_data.csv")


def cumulative(df):

    return df
