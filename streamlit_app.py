import numpy as np
import streamlit as st
from matplotlib.figure import Figure

from simulation import run_simulation
from data.collector import Collector
from data.design import Tank, Boiler, HouseConditions, Prices
from data.locationData import Location, myPlant
import post_processing as pp


@st.cache_data(max_entries=100, show_spinner=False)
def compute(inputs: dict) -> dict:
    """Simulation and post processing. Keeps only the summaries: a year at 1 min is too heavy to store."""
    coll = Collector(N_modules=inputs["n_modules"], module_cost=inputs["module_cost"],
                     installation=inputs["installation"])
    location = Location(name=myPlant.name, utc_offset=myPlant.utc_offset,
                        latitude=inputs["latitude"], longitude=inputs["longitude"],
                        tiltAngle=inputs["tilt"], azimuthAngle=inputs["azimuth"])

    results = run_simulation(house=HouseConditions(mean_daily_consumption=inputs["consumption"]),
                             tank=Tank(V=inputs["tank_V"]),
                             boiler=Boiler(V=inputs["boiler_V"], Q=inputs["boiler_Q"]),
                             coll=coll, location=location)

    prices = Prices(gas=inputs["gas"], el=inputs["el"])
    solar_frac, as_is, to_be = pp.kpi(results, prices, inputs["boiler_type"] == "Gas")

    return {
        "solar_frac": solar_frac,
        "savings": as_is - to_be,
        "fin": pp.financial_analysis(as_is, to_be, coll.capex, inputs["dr"] / 100, inputs["lifetime"]),
        "monthly": pp.monthly_analysis(results),
        "diss": pp.demand_dissatisfaction(results),
    }


def show_plot(draw):
    """draw(ax) fills the axes. Figure instead of pyplot: every user has a thread of their own."""
    fig = Figure(figsize=(9, 5), layout="tight")
    draw(fig.add_subplot())
    st.pyplot(fig)


@st.dialog("Cash flows", width="large")
def show_cash_flows(output):
    show_plot(lambda ax: pp.plot_cash_flows(output["fin"], ax))

@st.dialog("Monthly energy", width="large")
def show_monthly(output):
    show_plot(lambda ax: pp.plot_monthly(output["monthly"], ax))

@st.dialog("Unmet demand", width="large")
def show_dissatisfaction(output):
    show_plot(lambda ax: pp.plot_dissatisfaction(output["diss"], ax))


st.set_page_config(page_title="Solar thermal collector calculator", layout="wide")
st.title("Solar thermal collector calculator")

# Input column is larger
left, right = st.columns([2, 1], gap="large")

with left:
    inputs = {}

    with st.container(border=True):
        st.subheader("Plant")
        col1, col2 = st.columns(2)
        inputs["latitude"] = col1.number_input("Latitude [°] (north)", 0.0, 90.0, myPlant.latitude, 0.01, "%.4f")
        inputs["longitude"] = col2.number_input("Longitude [°]", -180.0, 180.0, myPlant.longitude, 0.01, "%.4f")
        inputs["tilt"] = col1.number_input("Panel tilt [°]", 0.0, 90.0, float(myPlant.tiltAngle), 1.0, "%.1f")
        inputs["azimuth"] = col2.number_input("Azimuth [°] (180 = south)", 0.0, 360.0, float(myPlant.azimuthAngle), 1.0, "%.1f")
        inputs["n_modules"] = col1.number_input("Number of modules", 1, 20, Collector().N_modules)
        consumption_options = list(range(50, 401, 25))
        inputs["consumption"] = col2.selectbox("Mean consumption [l/day] @45°C", consumption_options,
                                               consumption_options.index(HouseConditions().mean_daily_consumption))
        inputs["tank_V"] = col1.number_input("Tank volume [m³]", 0.05, 5.0, float(Tank().V), 0.01)
        inputs["boiler_V"] = col2.number_input("Boiler volume [m³]", 0.05, 5.0, float(Boiler().V), 0.01)
        inputs["boiler_Q"] = col1.number_input("Boiler power [W]", 100.0, 100000.0, float(Boiler().Q), 100.0, "%.0f")
        inputs["boiler_type"] = col2.radio("Existing boiler", ["Gas", "Electric"], horizontal=True)
        gas_boiler = inputs["boiler_type"] == "Gas"
        if gas_boiler:
            col2.caption("Gas boilers are often above 20 kW")

    with st.container(border=True):
        st.subheader("Costs")
        col1, col2 = st.columns(2)
        inputs["module_cost"] = col1.number_input("Cost per module [EUR]", 1.0, 100000.0, float(Collector().module_cost), 10.0, "%.0f")
        inputs["installation"] = col2.number_input("Installation cost [EUR]", 0.0, 1000000.0, float(Collector().installation), 100.0, "%.0f")
        # The gas price is not used with an electric boiler
        inputs["gas"] = col1.number_input("Gas price [EUR/m³]", 0.01, 100.0, float(Prices().gas), 0.01, disabled=not gas_boiler)
        inputs["el"] = col2.number_input("Electricity price [EUR/kWh]", 0.01, 100.0, float(Prices().el), 0.01)
        inputs["dr"] = col1.number_input("Discount rate [%]", 0.0, 100.0, 3.0, 0.5)
        inputs["lifetime"] = col2.number_input("Lifetime [years]", 1, 50, 20)

with right:
    st.subheader("Results")

    # Run next to the results, so they are in view when it finishes
    if st.button("Run", type="primary", width="stretch"):
        with st.spinner("Running..."):
            try:
                st.session_state["output"] = compute(inputs)
                st.session_state["output_inputs"] = dict(inputs)
            except Exception as err:    # e.g. no internet, or location not covered by PVGIS
                st.error(f"Simulation failed: {err}")

    output = st.session_state.get("output")

    if output is None:
        st.info("Set the inputs and press Run.")
    else:
        fin = output["fin"]
        if st.session_state["output_inputs"] != inputs:
            st.warning("Inputs changed: press Run to update the results.")

        st.metric("NPV", f"{fin['NPV']:.0f} EUR")
        st.metric("PBP", f"> {fin['years'][-1]} y" if np.isnan(fin["PBP"]) else f"{fin['PBP']:.1f} y")
        st.metric("Solar fraction", f"{output['solar_frac']:.1%}")
        st.metric("Savings", f"{output['savings']:.0f} EUR/year")

        # One button per chart, opening over the page
        if st.button("Cash flows", width="stretch"):
            show_cash_flows(output)
        if st.button("Monthly energy", width="stretch"):
            show_monthly(output)
        if st.button("Unmet demand", width="stretch"):
            show_dissatisfaction(output)
