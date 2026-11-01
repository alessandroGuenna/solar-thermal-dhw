from typing import NamedTuple

class Stream(NamedTuple):
    mdot: float   # [kg/s]
    T: float      # [°C] inlet temperature

def vessel_balance(M, T_old, inlets, Q, UA, T_amb, cp, dt):
    """Fully mixed vessel, explicit Euler. Outflow equals inflow and leaves at T_old."""
    H = sum(s.mdot * cp * (s.T - T_old) for s in inlets)   # [W]
    losses = UA * (T_old - T_amb)                          # [W]

    return T_old + dt / (M * cp) * (H + Q - losses)
    