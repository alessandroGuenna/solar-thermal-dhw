import pandas as pd

def expandTime(df: pd.DataFrame, dt: str = '1min'):

    dt_original = df.index[1] - df.index[0]

    if dt_original < pd.Timedelta(dt):
        originalStep = dt_original.total_seconds() / 60
        raise ValueError(
            f"Requested time step {dt} is coarser than the original {originalStep:.0f}min.\n"
            "This function can only up-sample data."
        )

    newIndex = pd.date_range(start=df.index[0],
                            end=df.index[-1] + dt_original,
                            freq=dt,
                            inclusive="left")

    return df.reindex(newIndex, method="ffill")