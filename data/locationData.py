from dataclasses import dataclass

@dataclass
class Location:
    name: str
    utc_offset: int
    latitude: float
    longitude: float
    tiltAngle: float
    azimuthAngle: float

myPlant = Location(name="Genoa",
                 utc_offset=1,
                 latitude=44.4056,
                 longitude=8.9463,
                 tiltAngle=50,
                 azimuthAngle=180
                 )