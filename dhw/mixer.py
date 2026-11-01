def mixer(mu, Tu, Tb, Tc):
    if mu == 0:
        mb = 0
        mc = 0
        diss = False
        return mb, mc, diss
    
    if Tb < Tu:
        mb = mu
        mc = 0
        diss = True
        return mb, mc, diss
    
    mb = mu * (Tu - Tc)/(Tb - Tc)
    mc = mu - mb
    diss = False
    
    return mb, mc, diss