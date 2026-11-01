import numpy as np
from matplotlib.ticker import MaxNLocator
from data.design import Prices
from data.constants import WATER

J_to_kWh = 1/3.6e6
LHV_ng = 50e6 * J_to_kWh # [kWh/kg]
rho_ng = 0.7 #[kg/m^3]
eta_b = 0.9
cp_w = WATER.cp
Tb_ref = 60 # [°C]


def kpi(results: dict, prices:Prices, gas_boiler: bool) -> dict:
    Qb = results["Qb"]
    dt = results["dt"]
    pump_state = results["pump_state"]
    mdot_u = results["mdot_u"]
    mb = results["mb"]
    Tu = results["Tu"]
    Tcw = results["T_cw"]
    Ttank = results["T3"]
    coll = results["coll"]
    boiler = results["boiler"]
    house = results["house"]
    T_house = house.T_amb
    
    E_solar = np.sum(mb*cp_w*(Ttank-Tcw)) * dt * J_to_kWh
    E_boiler = np.sum(Qb) * dt * J_to_kWh
    
    solar_frac = E_solar / (E_solar+E_boiler)
    
    # Savings compared to natural gas boiler
    c_ng = prices.gas / rho_ng # [EUR/kg]
    c_el = prices.el           # [EUR/kg]
    P_pump = coll.P_pump       # [W]
    
    E_pump = np.sum(P_pump*pump_state)*dt*J_to_kWh
    
    E_as_is = np.sum(mdot_u*cp_w*(Tu-Tcw) +
                     boiler.UA * (Tb_ref - T_house))*dt*J_to_kWh
    
    if gas_boiler:
        cost_as_is = E_as_is / eta_b / LHV_ng * c_ng
        cost_to_be = E_boiler / eta_b / LHV_ng * c_ng + E_pump*c_el
    else:
        cost_as_is = E_as_is * c_el
        cost_to_be = E_boiler * c_el + E_pump*c_el
    
    return solar_frac, cost_as_is, cost_to_be

def payback_period(years, cum_cf):
    """Payback period [years], linearly interpolated. NaN if never reached."""
    positive = np.flatnonzero(cum_cf >= 0)
    if len(positive) == 0:
        return np.nan   # investment never pays back

    k = positive[0]
    if k == 0:
        return 0.0

    # interpolate between year k-1 (negative) and year k (positive)
    return years[k-1] - cum_cf[k-1] / (cum_cf[k] - cum_cf[k-1])


def financial_analysis(as_is, to_be, capex, dr, lifetime=20):
    """Simple and discounted cash flows of the solar system vs the as-is.
    as_is, to_be: yearly operating costs [EUR/year]
    capex: initial investment [EUR]
    dr: discount rate [-], e.g. 0.03
    lifetime: economic lifetime [years]
    """
    years = np.arange(lifetime + 1)     # 0, 1, ..., lifetime

    cf = np.full(lifetime + 1, as_is - to_be, dtype=float)
    cf[0] = -capex                      # investment at year 0
    dcf = cf / (1 + dr)**years

    cum_cf = np.cumsum(cf)
    cum_dcf = np.cumsum(dcf)

    return {
        "years": years,
        "cum_cf": cum_cf,
        "cum_dcf": cum_dcf,
        "NPV": cum_dcf[-1],
        "PBP": payback_period(years, cum_cf),
        "DPBP": payback_period(years, cum_dcf),
    }


def plot_cash_flows(fin: dict, ax):
    """Grouped bars of the cumulative simple and discounted cash flows."""
    years = fin["years"]
    w = 0.4

    ax.bar(years - w/2, fin["cum_cf"], width=w*0.9, color="#2a78d6", label="Cumulative CF")
    ax.bar(years + w/2, fin["cum_dcf"], width=w*0.9, color="#eb6834", label="Cumulative DCF")
    ax.axhline(0, color="#0b0b0b", linewidth=0.8)

    # payback markers, labelled in the legend so they never overlap the bars
    for key, ls in (("PBP", ":"), ("DPBP", "--")):
        if np.isnan(fin[key]):
            # not reached within the lifetime: legend entry only
            ax.plot([], [], color="#52514e", linestyle=ls, linewidth=1,
                    label=f"{key} > {years[-1]} y")
        else:
            ax.axvline(fin[key], color="#52514e", linestyle=ls, linewidth=1,
                       label=f"{key} = {fin[key]:.1f} y")

    ax.set_xlabel("Year")
    ax.set_ylabel("Cumulative cash flow [EUR]")
    ax.set_xticks(years[::2])
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # legend below the axes: bars can fill any corner of the plot
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4)
    
    

def demand_dissatisfaction(results: dict, T_severe=35) -> dict:
    """Unmet demand: yearly total [h] and minutes per delivered temperature (1 °C bins).
    T_severe: delivered temperature below which the disservice is severe [°C]
    """
    diss = results["demand_diss"]
    Tb = results["Tb"]
    dt_min = results["dt"] / 60     # [min] per time step

    if not np.any(diss):
        return {"hours": 0.0, "hours_severe": 0.0, "T_severe": T_severe,
                "T_bins": np.array([]), "t": np.array([])}

    # floor, so every bin is strictly below the requested temperature
    T_diss = np.floor(Tb[diss]).astype(int)
    T_bins, counts = np.unique(T_diss, return_counts=True)

    return {
        "hours": np.count_nonzero(diss) * dt_min / 60,  # [h/year]
        "hours_severe": np.count_nonzero(Tb[diss] < T_severe) * dt_min / 60,   # [h/year]
        "T_severe": T_severe,                           # [°C]
        "T_bins": T_bins,                               # [°C]
        "t": counts * dt_min,                           # [min/year]
    }

def plot_dissatisfaction(d: dict, ax):
    """Histogram of the minutes of unmet demand by delivered temperature."""
    if d["hours"] == 0:
        ax.text(0.5, 0.5, "Demand always satisfied", transform=ax.transAxes,
                ha="center", va="center", color="#52514e")
        ax.set_axis_off()
        return

    ax.bar(d["T_bins"], d["t"], width=0.9, color="#2a78d6")

    ax.set_title(f"Unmet demand: {d['hours']:.1f} h/year  ·  "
                 f"below {d['T_severe']:.0f} °C: {d['hours_severe']:.1f} h/year", loc="left")
    ax.set_xlabel("Delivered temperature [°C]")
    ax.set_ylabel("Minutes per year [min]")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))   # bins are whole degrees
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
        
    
def monthly_analysis(results:dict) -> dict:
    """Monthly useful solar energy and boiler energy [kWh]."""
    dt = results["dt"]
    time = results["time"]

    P_solar = results["mb"] * cp_w * (results["T3"] - results["T_cw"])  # [W]
    Qb = results["Qb"]                                                  # [W]

    months = np.arange(1,13)

    E_solar = np.zeros(12)
    E_boiler = np.zeros(12)

    for idx, m in enumerate(months):
        mask = time.month == m
        E_solar[idx] = np.sum(P_solar[mask]) * dt*J_to_kWh
        E_boiler[idx] = np.sum(Qb[mask]) * dt*J_to_kWh

    return {"months": months, "E_solar": E_solar, "E_boiler": E_boiler}


def plot_monthly(monthly: dict, ax):
    """Stacked monthly bars: solar energy at the bottom, boiler energy on top."""
    months = monthly["months"]
    E_solar = monthly["E_solar"]
    E_boiler = monthly["E_boiler"]

    # white edge: thin gap between the two stacked segments
    ax.bar(months, E_solar, width=0.7, color="#2a78d6", edgecolor="white", label="Solar")
    ax.bar(months, E_boiler, width=0.7, bottom=E_solar, color="#eb6834", edgecolor="white", label="Boiler")

    ax.set_ylabel("Energy [kWh/month]")
    ax.set_xticks(months)
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2)


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from simulation import run_simulation
    
    while True:
        user_input = input("Type true for gas boiler, false for electric boiler [true/false]: ").strip().lower()
        
        if user_input == "true":
            gas_boiler = True
            break
        elif user_input == "false":
            gas_boiler = False
            break
        else:
            print("Invalid input")

    r = run_simulation()
    solar_frac, as_is, to_be = kpi(r, Prices(), gas_boiler)
    print(f"Solar fraction = {solar_frac:.3f}")
    print(f"AS-IS cost = {as_is:.2f} EUR")
    print(f"TO-BE cost = {to_be:.2f} EUR")

    capex = r["coll"].capex
    fin = financial_analysis(as_is, to_be, capex, dr=0.03)
    print(f"NPV = {fin['NPV']:.0f} EUR, PBP = {fin['PBP']:.1f} y, DPBP = {fin['DPBP']:.1f} y")

    fig, ax = plt.subplots(figsize=(9, 5))
    plot_cash_flows(fin, ax)
    fig.tight_layout()

    d = demand_dissatisfaction(r)
    print(f"Unmet demand = {d['hours']:.1f} h/year, below {d['T_severe']} °C = {d['hours_severe']:.1f} h/year")

    fig2, ax2 = plt.subplots(figsize=(9, 5))
    plot_dissatisfaction(d, ax2)
    fig2.tight_layout()

    fig3, ax3 = plt.subplots(figsize=(9, 5))
    plot_monthly(monthly_analysis(r), ax3)
    fig3.tight_layout()
    plt.show()