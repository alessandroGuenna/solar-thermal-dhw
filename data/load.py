from pathlib import Path
import numpy as np

def load_profile(avg_cons_daily):
    LOAD_DIR = Path(__file__).parent / "Load data" / f"sf_{avg_cons_daily}"

    file_num = (avg_cons_daily - 50) / 25  + 1

    file = LOAD_DIR / f"sf_{file_num:.0f}_DHW.txt"

    return np.loadtxt(file) # liters per hour