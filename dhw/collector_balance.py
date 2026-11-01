def collector_balance(T2_old, T1, C_th, eta_0, a, b, Tair, A_tot, C_hot, G, pump_state, dt):

    timestep_red_factor = 4
    dt_red = dt / timestep_red_factor

    if pump_state:
        for i in range(timestep_red_factor):
            Q = (eta_0 * G - a * (T2_old - Tair) - b * (T2_old - Tair)**2) * A_tot
            T2_new = T2_old + dt_red/C_th * (Q - C_hot * (T2_old - T1))
            T2_old = T2_new
        return T2_new
    else:
        for i in range(timestep_red_factor):
            Q = (eta_0 * G - a * (T2_old - Tair) - b * (T2_old - Tair)**2) * A_tot
            T2_new = T2_old + dt_red/C_th * Q
            T2_old = T2_new
        return T2_new