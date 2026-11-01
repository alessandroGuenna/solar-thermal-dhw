from dataclasses import dataclass
from CoolProp.CoolProp import PropsSI

@dataclass
class Water:
    rho: float = 1000 # [kg/m^3] density of water
    cp: float = 4186 # [J/kg K] specific heat capacity of water

@dataclass
class Refrigerant:
    fluid: str = "MPG" # Propylene glycol - water mixture
    mass_fraction: float = 0.4 # [kg/kg] mass fraction of propylene glycol in water
    @property
    def rho(self):
            return PropsSI('D', 'T', 300, 'P', 101325, f"INCOMP::{self.fluid}[{self.mass_fraction}]") # [kg/m^3]
    @property
    def cp(self):
        return PropsSI('C', 'T', 300, 'P', 101325, f"INCOMP::{self.fluid}[{self.mass_fraction}]") # [J/kg K]

WATER = Water()
REF = Refrigerant()