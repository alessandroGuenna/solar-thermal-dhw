# Solar thermal collector calculator

A Python model of a Domestic Hot Water (DHW) plant for a single-family house using flat plate solar thermal collectors.

Set the plant location and specifications, the utility prices and the average consumption: the program simulates a full year of operation with a 1 minute time step and returns the most relevant financial and performance indicators (NPV, payback period, solar fraction, annual savings), together with plots of the cash flows, the monthly energy and the unmet demand.

Full description of the app and of the model: <https://alessandroguenna.github.io/projects/thermal-collector/>

## How to use it

There are two ways to use the app, with the same model and the same results.

### Option 1: web app (nothing to install)

Open the app at <https://solar-thermal-dhw.streamlit.app/>

It runs in the browser, so it works on any device (PC, tablet or smartphone). The app is on a free hosting service that puts it to sleep after a period of inactivity: if you see a wake-up button, press it and wait a moment.

### Option 2: run it locally

You need **Python 3.12 or newer**. Download the repository (`Code > Download ZIP`, or `git clone`), open a terminal in its folder and run:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

On Linux and macOS, activate the environment with `source .venv/bin/activate` instead.

`requirements.txt` installs the exact versions the project was tested with:

| Library | Version | Used for |
|---|---|---|
| `numpy` | 2.5.4 | Simulation arrays and financial calculations |
| `pandas` | 3.1.0 | Weather data handling |
| `matplotlib` | 3.11.2 | Plots |
| `pydantic` | 2.14.2 | Plant and price parameters, with input validation |
| `pvlib` | 0.16.1 | Weather data download and irradiance on the tilted collector |
| `CoolProp` | 7.2.0 | Properties of the water/glycol mixture |
| `streamlit` | 1.66.1 | Web interface only, not needed by `app.py` |

`app.py` also uses `tkinter`, which is included with Python on Windows and macOS. On Linux you may have to install it separately (for example `sudo apt install python3-tk`).

To open the web interface on your own computer instead of the desktop window, run `streamlit run streamlit_app.py`.

**Internet connection:** weather data for the default configuration (Genoa, tilt 50°, azimuth 180°) is included, so the app works offline as long as these three inputs are unchanged. Any other location or panel orientation downloads its data from PVGIS and saves it in `data/Weather data/` for the next runs.

## What is in the repository

```text
app.py               Desktop app (tkinter)
streamlit_app.py     Web app (Streamlit)
simulation.py        Yearly simulation of the plant
post_processing.py   Financial analysis, performance indicators and plots
dhw/                 Component models: collector, heat exchanger, vessels, mixer
data/                Parameters of the plant, weather and load data
  Load data/         15 DHW load profiles, 50 to 400 l/day
  Weather data/      Typical meteorological year for the default location
utility/             Dark theme and time series helpers
requirements.txt     Python libraries
```

The settings used to generate the load profiles are in [`data/Load data/DHW_input.ini`](data/Load%20data/DHW_input.ini), and each profile folder contains the matching DHWcalc log file.

## Data sources and credits

- **Load profiles:** generated with [DHWcalc](https://www.uni-kassel.de/maschinenbau/en/institute/thermische-energietechnik/fachgebiete/solar-und-anlagentechnik/downloads), version 2.02b, University of Kassel. U. Jordan, K. Vajen, *DHWcalc: Program to generate domestic hot water profiles with statistical means for user defined conditions*, Proc. ISES Solar World Congress, Orlando, 2005.
- **Weather data:** typical meteorological year from [PVGIS](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en), European Commission, Joint Research Centre.
- **Weather data access and solar position and irradiance calculations:** [pvlib python](https://pvlib-python.readthedocs.io/). K. S. Anderson et al., *pvlib python: 2023 project update*, Journal of Open Source Software 8(92), 5994, 2023, [doi:10.21105/joss.05994](https://doi.org/10.21105/joss.05994).
- **Collector:** performance parameters of the Kloben FSK 2.0 flat plate collector, from the manufacturer's data sheet.
- **Cold water temperature:** correlation by Burch and Christensen (NREL, 2007).
