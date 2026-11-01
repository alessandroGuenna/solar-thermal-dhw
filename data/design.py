from pydantic import BaseModel, Field
from numpy import pi
from data.constants import WATER, REF
from typing import ClassVar

class CylindricalVessel(BaseModel):
    # Insulated cylindrical water vessel with h/d = 1

    V: float = Field(gt=0, description="Volume [m^3]")
    U: float = Field(default=0.6, gt=0, le=10,
                     description="Global heat exchange coefficient [W/m^2K]")

    @property
    def h(self) -> float:
        return (4 * self.V / pi) ** (1/3)

    @property
    def d(self) -> float:
        return self.h

    @property
    def ext_surface(self) -> float:
        return pi * self.d**2 / 4 * 2 + pi * self.d * self.h

    @property
    def UA(self) -> float:
        return self.U * self.ext_surface          # [W/K]

    @property
    def M(self) -> float:
        return self.V * WATER.rho                 # [kg]

class Tank(CylindricalVessel):
    V: float = Field(default=0.3, gt=0, description="Volume [m^3]")

class Boiler(CylindricalVessel):
    V: float = Field(default=0.13, gt=0, description="Volume [m^3]")
    Q: float = Field(default=2000, gt=0, description="Power [W]")

class HeatExchanger(BaseModel):
    UA: float = Field(default=1000, gt=0, description="Global heat exchange coefficient [W/K]")
    V: float = Field(default=1, gt=0, description="Total fluid volume inside the heat exchanger [litres]")
    M: float = Field(default=5, gt=0, description="Metal mass of the heat exchanger (steel) [kg]")

    Cr_design: float = Field(default=1.0, gt=0, le=5, description="Design capacity-rate ratio Cc/Ch [-]")

    def mdot(self, mdot_coll: float) -> float:
        """Portata del circuito serbatoio-HX [kg/s] per il Cr di progetto."""
        return mdot_coll * REF.cp / WATER.cp * self.Cr_design

    cp_steel: ClassVar[float] = 500  # [J/kgK] specific heat capacity of steel

    @property
    def Cm(self) -> float:
        # [J/K] heat capacity of the heat exchanger
        C_metal = self.M * self.cp_steel
        C_fluid = self.V/2 * 1e-3 * REF.rho * REF.cp
        C_water = self.V/2 * 1e-3 * WATER.rho * WATER.cp
        return C_metal + C_fluid + C_water
    
class Prices(BaseModel):
    gas: float = Field(default=1.1, gt=0, description="Gas price [€/m^3]")
    el: float = Field(default=0.25, gt=0, description="Electricity price [€/kWh]")

class HouseConditions(BaseModel):
    T_amb: float = Field(default=20, gt=10, description="Ambient temperature [°C]")
    T_dhw: ClassVar[float] = 45  # [°C] DHW draw-off temperature (DHWcalc / IEA Task 26)
    mean_daily_consumption: int = Field(default=200, ge=50, le=400, multiple_of=25,
                                        description="Mean daily DHW draw-off volume at 45 °C [l/day]")