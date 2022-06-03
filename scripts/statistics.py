from pathlib import Path
import pandas as pd

data_dir = Path("../data")

def cumulative(df, source_column="value", target_column="cumsum_value"):
    df[target_column] = df[source_column].cumsum()
    return df

def average(df):
    df['average_value'] = df["value"].mean()
    return df

def median(df):
    df['median_value'] = df["value"].median()
    return df

def quantile_90(df):
    df['quantile_90'] = df["value"].quantile(0.9)
    return df

def quantile_10(df):
    df['quantile_10'] = df["value"].quantile(0.1)
    return df

def maximum(df):
    df['max'] = df["value"].max()
    return df

def minimum(df):
    df['min'] = df["value"].min()
    return df


df = pd.read_csv(data_dir / "test_data.csv")
cumulative(df)
average(df)
median(df)
quantile_90(df)
quantile_10(df)
maximum(df)
minimum(df)

print(df)