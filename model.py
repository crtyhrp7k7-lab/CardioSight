"""
Closed-loop lumped-parameter (0D) cardiovascular model with an interatrial shunt.

Eight compartments: LV, RV, LA, RA (time-varying elastance with an exponential
passive pressure-volume relation), systemic arteries, systemic veins, pulmonary
arteries (capacitance) and a pulmonary venous reservoir.

Units: pressure mmHg, volume mL, time s, resistance mmHg*s/mL, compliance mL/mmHg.

Research model only. Not validated against patient data. Not for clinical use.
"""
import copy
import math

RHO = 1.06        # blood density, g/mL
MMHG = 1333.2     # dyn/cm^2 per mmHg
STATE = ('LV', 'RV', 'LA', 'RA', 'SA', 'SV', 'PA', 'PV')

# ----------------------------------------------------------------------------
# Digital twins.  Chamber tuple = (Ees, V0, A, B):
#   P = e(t)*Ees*(V-V0) + (1-e(t))*A*(exp(B*(V-V0))-1)
# ----------------------------------------------------------------------------
HFREF = dict(
    HR=78, Tmax=0.30, Ta=0.17,
    LV=(0.62, 30, 1.60, 0.0125), RV=(0.35, 20, 0.90, 0.0160),
    LA=(0.22, 15, 0.55, 0.0300), RA=(0.30, 10, 0.70, 0.0350),
    Csa=1.10, Csv=70.0, Cpa=2.2, Cpv=9.0,
    SVR=1.20, Rvs=0.03, PVR=0.150, Rpv=0.012,
    Rmv=0.004, Rav=0.03, Rtv=0.004, Rpvv=0.02,
    SBV=1700)

HFPEF = dict(
    HR=70, Tmax=0.30, Ta=0.17,
    LV=(3.2, 10, 0.55, 0.0330), RV=(0.60, 10, 0.80, 0.0220),
    LA=(0.30, 10, 0.50, 0.0420), RA=(0.35, 10, 0.70, 0.0360),
    Csa=0.85, Csv=60.0, Cpa=2.8, Cpv=7.0,
    SVR=1.32, Rvs=0.03, PVR=0.125, Rpv=0.012,
    Rmv=0.004, Rav=0.03, Rtv=0.004, Rpvv=0.02,
    SBV=1350)

TWINS = {'HFrEF': HFREF, 'HFpEF': HFPEF}

# Exercise state: heart rate, SVR scale, LV/RV Ees scale, recruited stressed volume (mL)
EXERCISE = {'HFrEF': dict(HR=110, svr=0.65, ino=1.20, dV=700),
            'HFpEF': dict(HR=100, svr=0.60, ino=1.15, dV=750)}


# ----------------------------------------------------------------------------
# Elements
# ----------------------------------------------------------------------------
def e_vent(t, T, Tmax):
    """Ventricular activation, 0..1."""
    t = t % T
    if t < Tmax:
        return 0.5 * (1 - math.cos(math.pi * t / Tmax))
    if t < 1.5 * Tmax:
        return 0.5 * (1 + math.cos(2 * math.pi * (t - Tmax) / Tmax))
    return 0.0


def e_atr(t, T, Ta):
    """Atrial activation, 0..1; atrial systole ends near ventricular onset."""
    t = (t + 0.9 * Ta) % T
    if t < Ta:
        return 0.5 * (1 - math.cos(2 * math.pi * t / Ta))
    return 0.0


def chamber_pressure(V, e, Ees, V0, A, B):
    return e * Ees * (V - V0) + (1 - e) * A * (math.exp(B * (V - V0)) - 1.0)


def ed_stiffness(chamber, V):
    """Passive end-diastolic stiffness dP/dV (mmHg/mL) at volume V."""
    _, V0, A, B = chamber
    return A * B * math.exp(B * (V - V0))


def shunt_flow(dP, d_mm, Cd=0.7):
    """Sharp-edged orifice. dP = P_LA - P_RA (mmHg). Returns mL/s, + = left to right."""
    if d_mm <= 0:
        return 0.0
    area = math.pi * (d_mm / 20.0) ** 2             # cm^2
    v = math.sqrt(2 * abs(dP) * MMHG / RHO)         # cm/s
    return math.copysign(Cd * area * v, dP)


def pressures(y, t, p):
    T = 60.0 / p['HR']
    ev = e_vent(t, T, p['Tmax'])
    ea = e_atr(t, T, p['Ta'])
    Vlv, Vrv, Vla, Vra, Vsa, Vsv, Vpa, Vpv = y
    pp = 0.0
    if p.get('peri'):
        Vref, phi, Kp = p['peri']
        x = (Vlv + Vrv + Vla + Vra - Vref) / phi
        if x > 0:
            pp = Kp * (math.exp(x) - 1.0)
    return dict(
        lv=chamber_pressure(Vlv, ev, *p['LV']) + pp, rv=chamber_pressure(Vrv, ev, *p['RV']) + pp,
        la=chamber_pressure(Vla, ea, *p['LA']) + pp, ra=chamber_pressure(Vra, ea, *p['RA']) + pp,
        sa=Vsa / p['Csa'], sv=Vsv / p['Csv'], pa=Vpa / p['Cpa'], pv=Vpv / p['Cpv'], peri=pp)


def flows(P, p, d_mm):
    pos = lambda x: x if x > 0 else 0.0
    return dict(
        mv=pos(P['la'] - P['lv']) / p['Rmv'], av=pos(P['lv'] - P['sa']) / p['Rav'],
        tv=pos(P['ra'] - P['rv']) / p['Rtv'], pvv=pos(P['rv'] - P['pa']) / p['Rpvv'],
        sys=(P['sa'] - P['sv']) / p['SVR'], vr=(P['sv'] - P['ra']) / p['Rvs'],
        pul=(P['pa'] - P['pv']) / p['PVR'], pvr=(P['pv'] - P['la']) / p['Rpv'],
        sh=shunt_flow(P['la'] - P['ra'], d_mm))


def deriv(y, t, p, d_mm):
    Q = flows(pressures(y, t, p), p, d_mm)
    return [Q['mv'] - Q['av'], Q['tv'] - Q['pvv'],
            Q['pvr'] - Q['mv'] - Q['sh'], Q['vr'] - Q['tv'] + Q['sh'],
            Q['av'] - Q['sys'], Q['sys'] - Q['vr'],
            Q['pvv'] - Q['pul'], Q['pul'] - Q['pvr']]


def rk4(y, t, dt, p, d_mm):
    k1 = deriv(y, t, p, d_mm)
    k2 = deriv([a + 0.5 * dt * b for a, b in zip(y, k1)], t + 0.5 * dt, p, d_mm)
    k3 = deriv([a + 0.5 * dt * b for a, b in zip(y, k2)], t + 0.5 * dt, p, d_mm)
    k4 = deriv([a + dt * b for a, b in zip(y, k3)], t + dt, p, d_mm)
    return [a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(y, k1, k2, k3, k4)]


# ----------------------------------------------------------------------------
# Simulation
# ----------------------------------------------------------------------------
def _init_state(p):
    y = [p['LV'][1] + 100, p['RV'][1] + 100, p['LA'][1] + 50, p['RA'][1] + 40]
    rest = p['SBV'] - 290
    Ct = p['Csa'] + p['Csv'] + p['Cpa'] + p['Cpv']
    return y + [rest * p[c] / Ct for c in ('Csa', 'Csv', 'Cpa', 'Cpv')]


def _set_sbv(y, p):
    """Make total stressed volume equal p['SBV']; any difference goes to the veins."""
    v0 = p['LV'][1] + p['RV'][1] + p['LA'][1] + p['RA'][1]
    y = list(y)
    y[5] += p['SBV'] - (sum(y) - v0)
    return y


def simulate(p, shunt_mm=0.0, y0=None, dt=0.0005, block=40, maxblocks=8, tol=0.02):
    """Run to steady state. Returns (metrics of the final beat, final state).

    Integrates in blocks of `block` beats until mean LA pressure changes by less
    than `tol` mmHg between blocks. `y0` warm-starts from a previous state.
    """
    T = 60.0 / p['HR']
    n = int(round(T / dt))
    y = _set_sbv(y0 if y0 else _init_state(p), p)
    prev = None
    for _ in range(maxblocks):
        for b in range(block):
            last = b == block - 1
            if last:
                rec = []
            for i in range(n):
                t = i * dt
                if last:
                    P = pressures(y, t, p)
                    rec.append((list(y), P, flows(P, p, shunt_mm)))
                y = rk4(y, t, dt, p, shunt_mm)
        mla = sum(r[1]['la'] for r in rec) / len(rec)
        if prev is not None and abs(mla - prev) < tol:
            break
        prev = mla

    mean = lambda f: sum(f(r) for r in rec) / len(rec)
    V = {k: [r[0][i] for r in rec] for i, k in enumerate(STATE)}
    Ppa = [r[1]['pa'] for r in rec]
    Psa = [r[1]['sa'] for r in rec]
    Qs = mean(lambda r: r[2]['av']) * 0.06
    Qp = mean(lambda r: r[2]['pvv']) * 0.06
    mRA = mean(lambda r: r[1]['ra'])
    m = dict(
        HR=p['HR'], CO=Qs, Qp=Qp, QpQs=Qp / Qs, Qsh=mean(lambda r: r[2]['sh']) * 0.06,
        PCWP=mla, LAv=max(r[1]['la'] for r in rec), LVEDP=rec[0][1]['lv'], RAP=mRA,
        LA_RA=mla - mRA,
        PAs=max(Ppa), PAd=min(Ppa), mPAP=sum(Ppa) / len(Ppa),
        Ppv=mean(lambda r: r[1]['pv']), PBV=mean(lambda r: r[0][6] + r[0][7]),
        AoS=max(Psa), AoD=min(Psa), MAP=sum(Psa) / len(Psa),
        LVEDV=max(V['LV']), LVESV=min(V['LV']), LVSV=max(V['LV']) - min(V['LV']),
        LVEF=100 * (max(V['LV']) - min(V['LV'])) / max(V['LV']),
        RVEDV=max(V['RV']), RVSV=max(V['RV']) - min(V['RV']),
        RVEF=100 * (max(V['RV']) - min(V['RV'])) / max(V['RV']),
        LAmax=max(V['LA']), RAmax=max(V['RA']),
        Pperi=mean(lambda r: r[1]['peri']),
        Vheart=max(sum(r[0][:4]) for r in rec), SBV=p['SBV'])
    return m, y


# ----------------------------------------------------------------------------
# Scenario helpers
# ----------------------------------------------------------------------------
def with_pericardium(p0, k=0.08, Kp=3.0):
    """Add a pericardial constraint referenced to the twin's own no-shunt heart size.

    P_peri = Kp*(exp((V_heart - V_ref)/(k*V_ref)) - 1) for V_heart > V_ref, else 0,
    so the resting no-shunt state is unchanged. Returns (params, steady state).
    """
    b0, y0 = simulate(p0)
    p = copy.deepcopy(p0)
    p['peri'] = (b0['Vheart'], k * b0['Vheart'], Kp)
    return p, y0


def exercise(p, kind, pvd=False):
    """Exercise state. pvd=True: PVR rises 40% and PA compliance falls 40%
    (pulmonary vascular disease) instead of PVR falling 15%."""
    q = copy.deepcopy(p)
    ex = EXERCISE[kind]
    q['HR'] = ex['HR']
    q['Tmax'], q['Ta'] = 0.24, 0.13
    q['SVR'] *= ex['svr']
    q['SBV'] += ex['dV']
    for ch in ('LV', 'RV'):
        E, V0, A, B = q[ch]
        q[ch] = (E * ex['ino'], V0, A, B)
    if pvd:
        q['PVR'] *= 1.40
        q['Cpa'] *= 0.60
    else:
        q['PVR'] *= 0.85
    return q


def solve_volume_arm(p, gain, map_set, y0, shunt_mm, hi=900.0, iters=9):
    """Steady-state stressed volume added by the volume arm of the reflex.

    dV = gain * (map_set - MAP(dV)), gain in mL/mmHg. gain = float('inf')
    restores mean arterial pressure to map_set. Returns (dV, metrics, params).
    """
    if gain == 0:
        r, _ = simulate(p, shunt_mm, y0=y0)
        return 0.0, r, p
    lo = 0.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        q = copy.deepcopy(p)
        q['SBV'] += mid
        r, _ = simulate(q, shunt_mm, y0=y0)
        deficit = map_set - r['MAP']
        g = deficit if gain == float('inf') else gain * max(deficit, 0.0) - mid
        if g > 0:
            lo = mid
        else:
            hi = mid
    return mid, r, q
