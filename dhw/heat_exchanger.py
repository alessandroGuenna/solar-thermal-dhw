import math

def effectiveness(C_hot, C_cold, UA):
    # Countercurrent heat exchanger, quasi steady
    C_min = min(C_hot, C_cold)
    C_max = max(C_hot, C_cold)
    NTU = UA / C_min
    Cr = C_min / C_max

    if math.isclose(Cr, 1.0, rel_tol=1e-6):
        eps = NTU / (1.0 + NTU)
    else:
        E = math.exp(-NTU * (1.0 - Cr))
        eps = (1.0 - E) / (1.0 - Cr * E)

    if not 0.0 < eps <= 1.0:
        raise ValueError(f"Effectiveness out of bounds: eps={eps} (NTU={NTU}, Cr={Cr})")

    return eps

def heat_exchanger(T_hot_in, T_cold_in, C_hot, C_cold, eps):

    q = eps * min(C_hot, C_cold) * (T_hot_in - T_cold_in)

    T_hot_out = T_hot_in - q / C_hot
    T_cold_out = T_cold_in + q / C_cold

    return q, T_hot_out, T_cold_out