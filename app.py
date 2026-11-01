from tkinter import Tk, Toplevel, StringVar, ttk, messagebox

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from utility.dark_theme import apply_dark_theme
from simulation import run_simulation
from data.collector import Collector
from data.design import Tank, Boiler, HouseConditions, Prices
from data.locationData import Location, myPlant
import post_processing as pp


def add_field(parent, row, key, text, default, kind, low, high):
    """Label + entry on one row, registered in fields to be read by read_inputs."""
    ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", pady=3)
    var = StringVar(value=str(default))
    entry = ttk.Entry(parent, textvariable=var, width=12)
    entry.grid(row=row, column=1, sticky="e", pady=3)
    fields[key] = {"var": var, "entry": entry, "text": text, "kind": kind, "low": low, "high": high}


def read_inputs() -> dict:
    """Text of every field converted to a number. ValueError if missing or out of range."""
    values = {}
    for key, field in fields.items():
        text = field["var"].get().strip()
        try:
            value = field["kind"](text)
        except ValueError:
            raise ValueError(f"{field['text']}: '{text}' is not a valid number.") from None
        if not field["low"] <= value <= field["high"]:
            raise ValueError(f"{field['text']}: must be between {field['low']} and {field['high']}.")
        values[key] = value
    return values


def on_boiler_type_change():
    # The gas price is not used with an electric boiler
    gas_boiler = boiler_type_var.get() == "gas"
    fields["gas"]["entry"].config(state="normal" if gas_boiler else "disabled")
    boiler_hint_var.set("Gas boilers are often above 20 kW" if gas_boiler else "")


def on_run():
    try:
        v = read_inputs()
        coll = Collector(N_modules=v["n_modules"], module_cost=v["module_cost"], installation=v["installation"])
        tank = Tank(V=v["tank_V"])
        boiler = Boiler(V=v["boiler_V"], Q=v["boiler_Q"])
        house = HouseConditions(mean_daily_consumption=int(consumption_var.get()))
        prices = Prices(gas=v["gas"], el=v["el"])
        location = Location(name=myPlant.name, utc_offset=myPlant.utc_offset,
                            latitude=v["latitude"], longitude=v["longitude"],
                            tiltAngle=v["tilt"], azimuthAngle=v["azimuth"])
    except ValueError as err:   # pydantic's ValidationError is a ValueError too
        messagebox.showerror("Invalid input", str(err))
        return

    status_var.set("Running...")
    root.update_idletasks()     # redraw now: the simulation blocks the window

    try:
        results = run_simulation(house=house, tank=tank, boiler=boiler, coll=coll, location=location)
    except Exception as err:    # e.g. no internet, or location not covered by PVGIS
        status_var.set("")
        messagebox.showerror("Simulation failed", str(err))
        return

    gas_boiler = boiler_type_var.get() == "gas"
    solar_frac, as_is, to_be = pp.kpi(results, prices, gas_boiler)
    lifetime = v["lifetime"]
    fin = pp.financial_analysis(as_is, to_be, coll.capex, v["dr"] / 100, lifetime)

    last["results"] = results
    last["fin"] = fin

    npv_var.set(f"{fin['NPV']:.0f} EUR")
    pbp_var.set(f"> {lifetime} y" if np.isnan(fin["PBP"]) else f"{fin['PBP']:.1f} y")
    solar_frac_var.set(f"{solar_frac:.1%}")
    savings_var.set(f"{as_is - to_be:.0f} EUR/year")
    status_var.set("Done")

    for button in plot_buttons:
        button.config(state="normal")


def open_plot(title, draw):
    """New window with a chart. draw(ax) fills the axes."""
    window = Toplevel(root)
    window.title(title)

    fig = Figure(figsize=(9, 5), layout="tight")
    ax = fig.add_subplot()
    draw(ax)

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    NavigationToolbar2Tk(canvas, window)    # zoom, pan, save
    canvas.get_tk_widget().pack(fill="both", expand=True)


def show_cash_flows():
    open_plot("Cash flows", lambda ax: pp.plot_cash_flows(last["fin"], ax))

def show_monthly():
    open_plot("Monthly energy", lambda ax: pp.plot_monthly(pp.monthly_analysis(last["results"]), ax))

def show_dissatisfaction():
    open_plot("Unmet demand", lambda ax: pp.plot_dissatisfaction(pp.demand_dissatisfaction(last["results"]), ax))


fields = {}     # filled by add_field
last = {}       # results of the latest run, used by the plot buttons

root = Tk()
apply_dark_theme(root)
root.geometry("900x680")
root.resizable(width=False, height=False)
root.title("Solar thermal collector calculator")

left = ttk.LabelFrame(root, text="Inputs", padding=12)
left.grid(row=0, column=0, sticky="nsew")
left.columnconfigure(0, weight=1)

right = ttk.LabelFrame(root, text="Results", padding=12)
right.grid(row=0, column=1, sticky="nsew")
right.columnconfigure(0, weight=1)

# Input column is larger
root.columnconfigure(0, weight=2, uniform="col")
root.columnconfigure(1, weight=1, uniform="col")
root.rowconfigure(0, weight=1)

# Inputs: plant
plant_frame = ttk.LabelFrame(left, text="Plant", padding=8)
plant_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
plant_frame.columnconfigure(0, weight=1)

add_field(plant_frame, 0, "latitude", "Latitude [°] (north)", myPlant.latitude, float, 0, 90)
add_field(plant_frame, 1, "longitude", "Longitude [°]", myPlant.longitude, float, -180, 180)
add_field(plant_frame, 2, "tilt", "Panel tilt [°]", myPlant.tiltAngle, float, 0, 90)
add_field(plant_frame, 3, "azimuth", "Azimuth [°] (180 = south)", myPlant.azimuthAngle, float, 0, 360)
add_field(plant_frame, 4, "n_modules", "Number of modules", Collector().N_modules, int, 1, 20)
add_field(plant_frame, 5, "tank_V", "Tank volume [m³]", Tank().V, float, 0.05, 5)
add_field(plant_frame, 6, "boiler_V", "Boiler volume [m³]", Boiler().V, float, 0.05, 5)
add_field(plant_frame, 7, "boiler_Q", "Boiler power [W]", Boiler().Q, float, 100, 100000)

ttk.Label(plant_frame, text="Existing boiler").grid(row=8, column=0, sticky="w", pady=3)
boiler_type_var = StringVar(value="gas")
radio_frame = ttk.Frame(plant_frame)
radio_frame.grid(row=8, column=1, sticky="e", pady=3)
ttk.Radiobutton(radio_frame, text="Gas", variable=boiler_type_var, value="gas",
                command=on_boiler_type_change).pack(side="left")
ttk.Radiobutton(radio_frame, text="Electric", variable=boiler_type_var, value="electric",
                command=on_boiler_type_change).pack(side="left")

boiler_hint_var = StringVar()
ttk.Label(plant_frame, textvariable=boiler_hint_var).grid(row=9, column=0, columnspan=2, sticky="e")

ttk.Label(plant_frame, text="Mean consumption [l/day] @45°C").grid(row=10, column=0, sticky="w", pady=3)
consumption_var = StringVar(value=str(HouseConditions().mean_daily_consumption))
ttk.Combobox(plant_frame, textvariable=consumption_var, width=10, state="readonly",
             values=[str(v) for v in range(50, 401, 25)]).grid(row=10, column=1, sticky="e", pady=3)

# Inputs: costs
costs_frame = ttk.LabelFrame(left, text="Costs", padding=8)
costs_frame.grid(row=1, column=0, sticky="ew")
costs_frame.columnconfigure(0, weight=1)

add_field(costs_frame, 0, "module_cost", "Cost per module [EUR]", Collector().module_cost, float, 1, 100000)
add_field(costs_frame, 1, "installation", "Installation cost [EUR]", Collector().installation, float, 0, 1000000)
add_field(costs_frame, 2, "gas", "Gas price [EUR/m³]", Prices().gas, float, 0.01, 100)
add_field(costs_frame, 3, "el", "Electricity price [EUR/kWh]", Prices().el, float, 0.01, 100)
add_field(costs_frame, 4, "dr", "Discount rate [%]", 3, float, 0, 100)
add_field(costs_frame, 5, "lifetime", "Lifetime [years]", 20, int, 1, 50)

ttk.Button(left, text="Run", command=on_run).grid(row=2, column=0, sticky="ew", pady=(10, 2))
status_var = StringVar()
ttk.Label(left, textvariable=status_var).grid(row=3, column=0, sticky="w")

on_boiler_type_change()

# Results: main values, updated by on_run
npv_var = StringVar(value="-")
pbp_var = StringVar(value="-")
solar_frac_var = StringVar(value="-")
savings_var = StringVar(value="-")

for row, (text, var) in enumerate([("NPV", npv_var), ("PBP", pbp_var),
                                   ("Solar fraction", solar_frac_var), ("Savings", savings_var)]):
    ttk.Label(right, text=text).grid(row=row, column=0, sticky="w", pady=4)
    ttk.Label(right, textvariable=var).grid(row=row, column=1, sticky="e", pady=4)

# Results: one button per chart, enabled after the first run
plot_buttons = []
for row, (text, command) in enumerate([("Cash flows", show_cash_flows),
                                       ("Monthly energy", show_monthly),
                                       ("Unmet demand", show_dissatisfaction)], start=4):
    button = ttk.Button(right, text=text, command=command, state="disabled")
    button.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16 if row == 4 else 2, 2))
    plot_buttons.append(button)

root.mainloop()
