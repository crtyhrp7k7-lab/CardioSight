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
    HR=72, Tmax=0.30, Ta=0.17,
    LV=(1.05, 30, 1.60, 0.0170), RV=(0.38, 20, 0.90, 0.0160),
    LA=(0.22, 15, 0.55, 0.0300), RA=(0.30, 10, 0.70, 0.0350),
    Csa=1.10, Csv=70.0, Cpa=2.2, Cpv=9.0,
    SVR=1.15, Rvs=0.03, PVR=0.150, Rpv=0.012,
    Rmv=0.004, Rav=0.03, Rtv=0.004, Rpvv=0.02,
    SBV=1716)

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


def passive_pressure(V, Ees, V0, A, B):
    return A * (math.exp(B * (V - V0)) - 1.0)


import os
SHUNT_CD = float(os.environ.get('SHUNT_CD', 0.7))   # orifice discharge coefficient


def ed_stiffness(chamber, V):
    """Passive end-diastolic stiffness dP/dV (mmHg/mL) at volume V."""
    _, V0, A, B = chamber
    return A * B * math.exp(B * (V - V0))


def shunt_flow(dP, d_mm, Cd=None):
    """Sharp-edged orifice. dP = P_LA - P_RA (mmHg). Returns mL/s, + = left to right.
    Cd defaults to SHUNT_CD (0.7, or the SHUNT_CD environment variable)."""
    if Cd is None:
        Cd = SHUNT_CD
    if d_mm <= 0:
        return 0.0
    area = math.pi * (d_mm / 20.0) ** 2             # cm^2
    v = math.sqrt(2 * abs(dP) * MMHG / RHO)         # cm/s
    return math.copysign(Cd * area * v, dP)


def regurgitant_flow(dP, eroa_cm2):
    """Backward flow through an incompetent AV valve (mL/s), orifice law with the
    effective regurgitant orifice area (EROA, cm^2) as the effective area.
    dP = ventricular minus atrial pressure; flow only when dP > 0."""
    if eroa_cm2 <= 0 or dP <= 0:
        return 0.0
    return eroa_cm2 * math.sqrt(2 * dP * MMHG / RHO)


def pressures(y, t, p):
    T = 60.0 / p['HR']
    ev = e_vent(t, T, p['Tmax'])
    ea = 0.0 if p.get('afib') else e_atr(t, T, p['Ta'])    # afib: no atrial contraction
    Vlv, Vrv, Vla, Vra, Vsa, Vsv, Vpa, Vpv = y
    pp = 0.0
    if p.get('peri'):
        Vref, phi, Kp = p['peri']
        x = (Vlv + Vrv + Vla + Vra - Vref) / phi
        if x > 0:
            pp = Kp * (math.exp(x) - 1.0)
    sl = sr = 0.0
    if p.get('septum'):
        # Diastolic ventricular interaction, referenced to the no-shunt beat so that
        # baseline is unchanged: a rise in one ventricle's passive pressure above its
        # baseline value at the same phase is partly transmitted to the other.
        s = p['septum']
        x = (t % T) / s['dt']
        i = int(x) % s['n']
        j = (i + 1) % s['n']
        f = x - int(x)
        base_rv = s['rv'][i] + f * (s['rv'][j] - s['rv'][i])
        base_lv = s['lv'][i] + f * (s['lv'][j] - s['lv'][i])
        sl = s['beta_rl'] * (1 - ev) * (passive_pressure(Vrv, *p['RV']) - base_rv)
        sr = s['beta_lr'] * (1 - ev) * (passive_pressure(Vlv, *p['LV']) - base_lv)
    return dict(
        lv=chamber_pressure(Vlv, ev, *p['LV']) + pp + sl, rv=chamber_pressure(Vrv, ev, *p['RV']) + pp + sr,
        la=chamber_pressure(Vla, ea, *p['LA']) + pp, ra=chamber_pressure(Vra, ea, *p['RA']) + pp,
        sa=Vsa / p['Csa'], sv=Vsv / p['Csv'], pa=Vpa / p['Cpa'], pv=Vpv / p['Cpv'], peri=pp)


def flows(P, p, d_mm):
    pos = lambda x: x if x > 0 else 0.0
    return dict(
        mv=pos(P['la'] - P['lv']) / p['Rmv'], av=pos(P['lv'] - P['sa']) / p['Rav'],
        tv=pos(P['ra'] - P['rv']) / p['Rtv'], pvv=pos(P['rv'] - P['pa']) / p['Rpvv'],
        sys=(P['sa'] - P['sv']) / p['SVR'], vr=(P['sv'] - P['ra']) / p['Rvs'],
        pul=(P['pa'] - P['pv']) / p['PVR'], pvr=(P['pv'] - P['la']) / p['Rpv'],
        sh=shunt_flow(P['la'] - P['ra'], d_mm),
        mr=regurgitant_flow(P['lv'] - P['la'], p.get('MR', 0.0)),
        tr=regurgitant_flow(P['rv'] - P['ra'], p.get('TR', 0.0)))


def deriv(y, t, p, d_mm):
    Q = flows(pressures(y, t, p), p, d_mm)
    return [Q['mv'] - Q['mr'] - Q['av'], Q['tv'] - Q['tr'] - Q['pvv'],
            Q['pvr'] - Q['mv'] + Q['mr'] - Q['sh'], Q['vr'] - Q['tv'] + Q['tr'] + Q['sh'],
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


def simulate(p, shunt_mm=0.0, y0=None, dt=0.0005, block=40, maxblocks=8, tol=0.02, trace=False):
    """Run to steady state. Returns (metrics of the final beat, final state).

    Integrates in blocks of `block` beats until mean LA pressure changes by less
    than `tol` mmHg between blocks. `y0` warm-starts from a previous state.
    trace=True adds m['trace']: the final beat's time, chamber volumes and pressures
    (every 4th step), for plotting.
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
    # Ventriculo-arterial coupling, Ees/Ea. Ees = the chamber's end-systolic elastance
    # parameter; Ea = end-systolic pressure / stroke volume. End-systole is taken at
    # end-ejection, not at minimum volume: with MR/TR the ventricle keeps emptying
    # backwards through isovolumic relaxation, so minimum volume falls at a much lower
    # pressure and Ea would be underestimated. End-ejection = the last sample of the
    # forward outflow that contains peak ventricular pressure (walking forward from the
    # peak), so a brief valve opening at end-diastole (low PA diastolic pressure) is ignored.
    for ch, i, key, valve in (('RV', 1, 'rv', 'pvv'), ('LV', 0, 'lv', 'av')):
        k = max(range(len(rec)), key=lambda j: rec[j][1][key])
        if rec[k][2][valve] > 0:
            while k + 1 < len(rec) and rec[k + 1][2][valve] > 0:
                k += 1
        else:  # no forward flow at peak pressure: fall back to minimum volume
            k = min(range(len(rec)), key=lambda j: rec[j][0][i])
        Ea = rec[k][1][key] / m[ch + 'SV']
        m[ch + '_Ees'], m[ch + '_Ea'], m[ch + '_coupling'] = p[ch][0], Ea, p[ch][0] / Ea
    # Valve regurgitation per beat (mL) and regurgitant fraction of total stroke volume.
    m['LVFSV'] = sum(r[2]['av'] for r in rec) * dt            # forward (aortic) stroke volume
    m['MR_RVol'] = sum(r[2]['mr'] for r in rec) * dt
    m['TR_RVol'] = sum(r[2]['tr'] for r in rec) * dt
    m['MR_RF'] = 100 * m['MR_RVol'] / m['LVSV'] if m['LVSV'] > 0 else 0.0
    m['TR_RF'] = 100 * m['TR_RVol'] / m['RVSV'] if m['RVSV'] > 0 else 0.0
    if trace:
        sel = rec[::4]
        m['trace'] = dict(
            t=[i * 4 * dt for i in range(len(sel))],
            **{'V' + k: [r[0][i] for r in sel] for i, k in enumerate(STATE[:4])},
            **{'P' + k.upper(): [r[1][k] for r in sel] for k in ('lv', 'rv', 'la', 'ra', 'sa', 'pa')})
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


def with_septum(p, y0, beta_rl, beta_lr=0.1, dt=0.0005):
    """Add diastolic ventricular interaction referenced to the no-shunt resting beat.

    beta_rl: fraction of the rise in RV passive pressure (above its baseline value at
    the same phase) transmitted to LV pressure; beta_lr: the reverse. Records one
    baseline beat from the steady state y0. Valid only at the baseline heart rate.
    """
    T = 60.0 / p['HR']
    n = int(round(T / dt))
    y, rv, lv = list(y0), [], []
    for i in range(n):
        rv.append(passive_pressure(y[1], *p['RV']))
        lv.append(passive_pressure(y[0], *p['LV']))
        y = rk4(y, i * dt, dt, p, 0.0)
    q = copy.deepcopy(p)
    q['septum'] = dict(beta_rl=beta_rl, beta_lr=beta_lr, dt=dt, n=n, rv=rv, lv=lv)
    return q


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
