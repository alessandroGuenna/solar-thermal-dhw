import pvlib
import pandas as pd
from data.locationData import Location
from pathlib import Path
import numpy as np

DATA_DIR = Path(__file__).parent / "Weather data"

def get_tmy(plant: Location):

    # The file name must identify the data: same name means same coordinates and orientation
    cache = DATA_DIR / f"tmy_{plant.latitude:.4f}_{plant.longitude:.4f}_{plant.tiltAngle:g}_{plant.azimuthAngle:g}.csv"

    # First check if the data is already cached, if so return it
    if cache.is_file():
        out = pd.read_csv(cache, index_col=0, parse_dates=True)
        return out

    # If not, get the data from PVGIS and cache it
    else:
        data, _ = pvlib.iotools.get_pvgis_tmy(
            plant.latitude, plant.longitude,
            usehorizon=True,
            startyear=2013,
            endyear=2023,
            roll_utc_offset=plant.utc_offset,
            coerce_year=2023)

        solPos = pvlib.solarposition.get_solarposition(
            time=data.index + pd.Timedelta('30min'),
            latitude=plant.latitude,
            longitude=plant.longitude)

        solPos.index = data.index

        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=plant.tiltAngle,
            surface_azimuth=plant.azimuthAngle,
            dni=data['dni'],
            ghi=data['ghi'],
            dhi=data['dhi'],
            solar_zenith=solPos['apparent_zenith'],
            solar_azimuth=solPos['azimuth'],
            dni_extra=pvlib.irradiance.get_extra_radiation(data.index),
            model='haydavies')

        out = pd.DataFrame({
            'T': data['temp_air'],
            'G_T': poa['poa_global']
        })

        out.to_csv(cache, index=True)

        return out

##########################################################################################################

def cold_water_temperature(T_air: pd.Series) -> pd.Series:
    """Cold water from network [°C] from air temp [°C] (Burch & Christensen, NREL 2007)."""
    T_F = T_air * 9 / 5 + 32
    monthly = T_F.groupby(T_F.index.month).mean()

    T_avg = monthly.mean()
    dT_max = monthly.max() - monthly.min()

    ratio = 0.4 + 0.01 * (T_avg - 44)
    lag = 35 - 1.0 * (T_avg - 44)

    doy = T_air.index.dayofyear
    T_mains_F = (T_avg + 6) + ratio * dT_max / 2 * np.sin(np.radians(0.986 * (doy - 15 - lag) - 90))

    return pd.Series((T_mains_F - 32) * 5 / 9, index=T_air.index, name='T_cw')