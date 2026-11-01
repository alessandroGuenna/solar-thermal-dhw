from pydantic import BaseModel, Field
from typing import ClassVar
from data.constants import REF

class Collector(BaseModel):
    eta_0: float = Field(default=0.785, description="Collector efficiency at zero loss")
    a: float = Field(default=3.594, description="First order heat losses [W/m^2 K]")
    b: float = Field(default=0.014, description="Second order heat losses [W/m^2 K^2]")
    C_th_specific: float = Field(default=9543, description="Specific thermal capacity [J/m^2K]")
    A_module: float = Field(default=1.84, description="Area of a single module [m^2]")
    N_modules: int = Field(default=4, description="Number of modules")
    m_dot_sugg: float = Field(default=0.45, description="Suggested mass flow rate of the fluid (Kloben FSK 2.0) ([l/(m^2 min)]")
    module_cost: float = Field(default=450, gt=0, description="Cost of a single module in EUR (estimate)")
    installation: float = Field(default=2000, ge=0, description="Fixed installation cost: labour, circulation group, piping, mounting, VAT incl. (estimate) [€]")
    
    @property
    def capex(self):
        return self.N_modules*self.module_cost+self.installation
    
    @property
    def A_tot(self):
        return self.A_module * self.N_modules

    @property
    def m_fluid(self):
        return self.m_dot_sugg * self.A_tot / 60 * 1e-3 * REF.rho  # [kg/s]

    @property
    def C_th(self):
        return self.C_th_specific * self.A_tot  # [J/K]

    P_pump: ClassVar[float] = 30 # [W]