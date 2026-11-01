import numpy as np
import data.weather as weather
from data.load import load_profile
from data.locationData import Location, myPlant
import utility.helpers as helpers
from dhw import collector_balance, effectiveness, heat_exchanger, mixer, Stream, vessel_balance
from data.collector import Collector
from data.design import Tank, Boiler, HeatExchanger, HouseConditions
from data.constants import WATER, REF


def run_simulation(house: HouseConditions | None = None,
                   tank: Tank | None = None,
                   boiler: Boiler | None = None,
                   coll: Collector | None = None,
                   hx: HeatExchanger | None = None,
                   location: Location = myPlant,
                   dt: int = 60) -> dict:
    """Run the yearly simulation of the solar DHW plant.
    Every component left as None uses its default parameters.
    dt: time step [s]
    """
    house = house or HouseConditions()
    tank = tank or Tank()
    boiler = boiler or Boiler()
    coll = coll or Collector()
    hx = hx or HeatExchanger()

    # Fluid properties
    cp_f = REF.cp
    rho_w = WATER.rho
    cp_w = WATER.cp

    wData = weather.get_tmy(location)
    if (wData['G_T'] < 0).any():
        raise ValueError("Irradiance data contains negative values.")

    dt_string = f"{dt/60:.0f}min"

    wData = helpers.expandTime(wData, dt=dt_string)

    # unpack the weather data
    Tair = wData['T'].to_list()      # [°C]
    G = wData['G_T'].to_list()       # [W/m^2]
    T_cw = weather.cold_water_temperature(wData['T']).to_list()   # [°C]

    N = len(wData)

    # Unpack collector parameters
    eta_0 = coll.eta_0
    C_th_coll = coll.C_th
    A_coll = coll.A_tot
    a = coll.a
    b = coll.b
    mdot_f = coll.m_fluid
    C_hot = mdot_f * cp_f

    # Unpack heat exchanger parameters
    UA_hx = hx.UA
    mdot_hx = hx.mdot(mdot_f)
    C_cold = mdot_hx * cp_w

    # Unpack house conditions
    T_amb = house.T_amb
    avg_daily_cons = house.mean_daily_consumption # [l/day]

    # Load [kg/s]
    mdot_u = load_profile(avg_daily_cons) / 3600 / 1000 * rho_w
    if len(mdot_u) != N:
        raise ValueError(f"Load profile has {len(mdot_u)} values, expected {N}.")
    Tu = house.T_dhw

    # Point 1 is the collector's inlet
    T1 = np.full(N, np.nan)

    # Point 2 is inside the collector (lumped parameter model)
    T2 = np.full(N, np.nan)
    T2[0] = 30 # [°C] initial condition, over 1 year simulation, this will not affect the results

    # Point 3 is the tank temperature
    T3 = np.full(N, np.nan)
    T3[0] = 30 # [°C] initial condition

    # Point 4 is after the HX in the tank loop
    T4 = np.full(N, np.nan)

    # Boiler (lumped parameter model)
    Tb = np.full(N, np.nan)
    Tb[0] = 55 # [°C] initial condition

    # Heat exchanger effectivness
    # It's constant because both collector and tank loop work at constant flow rate (and cp)
    eps = effectiveness(C_hot, C_cold, UA_hx)
    q_hx = np.full(N, np.nan)

    # Mixer flow rates [kg/s] and boiler heat input [W], stored for post processing
    mb = np.zeros(N)
    mc = np.zeros(N)
    Qb = np.zeros(N)
    
    # Demand dissatisfaction vector
    diss = [False] * N

    # Pumps state, boolean
    pump_state = [False] * N
    boiler_state = [False] * N

    for i in range(N-1):
        # hysteresis to switch on/off the pumps
        # it's not important how large the dead band is, but just having one to avoid very frequent startup/stops
        T_ON = T3[i] + 4
        T_OFF = T3[i] + 2

        if pump_state[i]:
            q_hx[i], T1[i], T4[i] = heat_exchanger(T2[i], T3[i], C_hot, C_cold, eps)
        else:
            q_hx[i] = 0
            T1[i] = T2[i]
            T4[i] = T3[i]

        T2[i+1] = collector_balance(T2[i], T1[i], C_th_coll, eta_0, a, b, Tair[i], A_coll, C_hot, G[i], pump_state[i], dt)

        # Keep the tank in safe conditions
        safety_ON = T3[i] > 75
        safety_OFF = T3[i] < 72

        if pump_state[i] == False and T2[i] > T_ON and safety_OFF:
            pump_state[i+1] = True
        elif pump_state[i] == True and (T2[i] < T_OFF or safety_ON):
            pump_state[i+1] = False
        else:
            pump_state[i+1] = pump_state[i]

        # Mixer for outlet
        mb[i], mc[i], diss[i] = mixer(mdot_u[i], Tu, Tb[i], T_cw[i])

        # Boiler energy balance
        Tb_ON = 57
        Tb_OFF = 63

        if boiler_state[i] == False and Tb[i] < Tb_ON:
            boiler_state[i+1] = True
        elif boiler_state[i] == True and Tb[i] > Tb_OFF:
            boiler_state[i+1] = False
        else:
            boiler_state[i+1] = boiler_state[i]

        Qb[i] = boiler_state[i] * boiler.Q

        Tb[i+1] = vessel_balance(boiler.M, Tb[i], [Stream(mb[i], T3[i])],
                                 Qb[i], boiler.UA, T_amb, cp_w, dt)

        # Tank energy balance
        if pump_state[i]:
            in1 = Stream(mdot_hx, T4[i])
        else:
            in1 = Stream(0, 0)

        in2 = Stream(mb[i], T_cw[i])
        inlets = [in1, in2]
        T3[i+1] = vessel_balance(tank.M, T3[i], inlets, 0, tank.UA, T_amb, cp_w, dt)

    # Last time step: heat exchanger outputs (state variables are already known at N-1)
    if pump_state[N-1]:
        q_hx[N-1], T1[N-1], T4[N-1] = heat_exchanger(T2[N-1], T3[N-1], C_hot, C_cold, eps)
    else:
        q_hx[N-1] = 0
        T1[N-1] = T2[N-1]
        T4[N-1] = T3[N-1]

    # Last time step: mixer and boiler heat input
    mb[N-1], mc[N-1], diss[N-1] = mixer(mdot_u[N-1], Tu, Tb[N-1], T_cw[N-1])
    Qb[N-1] = boiler_state[N-1] * boiler.Q

    return {
        # inputs, to keep results self-contained
        "time": wData.index,
        "dt": dt,
        "house": house, "tank": tank, "boiler": boiler, "coll": coll, "hx": hx,
        "Tair": np.asarray(Tair),     # [°C]
        "G": np.asarray(G),           # [W/m^2]
        "T_cw": np.asarray(T_cw),     # [°C]
        "Tu": Tu,                     # [°C]
        "mdot_u": mdot_u,             # [kg/s]
        # results
        "T1": T1, "T2": T2, "T3": T3, "T4": T4, "Tb": Tb,   # [°C]
        "q_hx": q_hx,                 # [W]
        "Qb": Qb,                     # [W]
        "mb": mb, "mc": mc,           # [kg/s]
        "pump_state": np.asarray(pump_state),
        "boiler_state": np.asarray(boiler_state),
        "demand_diss": np.array(diss)
    }
