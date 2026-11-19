"""Scenario builder: one patient, any combination of shunt, valve disease and therapies.

Used by the GUI (launcher.py) and usable from Python:

    from scenario import DEFAULTS, run_scenario
    s = dict(DEFAULTS, twin='HFpEF', shunt_mm=8, bat=0.5, padn=True)
    out = run_scenario(s)
    print(out['base']['PCWP'], out['scen']['PCWP'])

The scenario is compared against the SAME patient (twin + patient modifiers + valve
disease + rhythm + rest/exercise state) with no shunt and no therapy.

Order of construction (follows run_triple.py, with additions marked NEW):
 1. Patient: twin parameters x patient modifiers; MR/TR as effective regurgitant
    orifice areas (NEW); atrial fibrillation = no atrial contraction.
 2. Chronic compensation of valve disease / AF (NEW, optional): stressed volume is added
    by a volume arm dV = gain x (MAP without lesion - MAP); default gain 20 mL/mmHg (the
    HFrEF shunt fit); 'inf' restores MAP fully. Capped at VOLUME_CAP with a warning.
 3. Pericardium referenced to that patient's own resting heart volume (unchanged baseline).
 4. Optional diastolic septal interaction (rest only; it is referenced to the resting beat).
 5. Therapies at rest:
      shunt (chronic)  post-shunt PVR rise x (1 - BAT)(1 - PADN); volume arm with the
                       twin's gain, retained volume x (1 - BAT)
      BAT              SVR -10%, HR -5%, stressed volume -4% at full strength
      PADN             resting PVR -10%; removes the post-shunt PVR rise and the exercise
                       pulmonary-vascular-disease response
      sotatercept      PVR x (1 - 30% x strength) (NEW). Anchor: PULSAR 0.7 mg/kg,
                       placebo-corrected PVR -239.5 dyn.s/cm5 (Humbert, NEJM 2021). The
                       percentage depends on baseline PVR and is an assumption.
 6. Exercise (optional): twin exercise state built from the patient; PVR follows the
    resting (treated) PVR; with PVD it rises by 40% and PA compliance falls by 40%,
    both scaled by (1 - PADN).
All therapy effect sizes are assumptions and can be edited in ASSUMPTIONS / the GUI.
"""
import copy
import math

import model
from model import TWINS, simulate, with_pericardium, with_septum, solve_volume_arm, exercise

INF = float('inf')

# Effective regurgitant orifice area (cm^2) per severity class. Guideline EROA classes
# (ACC/AHA 2020 MR; ASE 2017 TR): mild < 0.20, moderate 0.20-0.39, severe >= 0.40.
MR_EROA = {'none': 0.0, 'mild': 0.10, 'moderate': 0.30, 'severe': 0.50}
TR_EROA = {'none': 0.0, 'mild': 0.10, 'moderate': 0.30, 'severe': 0.70}
# Calibration (run 2026-11-19, uncompensated, no shunt): MR 0.10/0.30/0.50 cm^2 gives
# RVol about 14-17 / 37-41 / 54-57 mL, RF 20 / 43 / 54%; TR 0.60 cm^2 gave 40-44 mL
# (moderate by RVol), so severe TR uses 0.70 cm^2.

# Chronic shunt response, best fits from run_echo_matrix.py
VOLUME_CAP = 900.0     # mL, upper bound of the retained-volume search (as in model.solve_volume_arm)

FIT = {'HFrEF': dict(gain=20.0, pvr_rise=0.0), 'HFpEF': dict(gain=INF, pvr_rise=0.5)}

ASSUMPTIONS = dict(bat_svr=0.10, bat_hr=0.05, bat_sbv=0.04, padn_pvr=0.10, sota_pvr=0.30)

DEFAULTS = dict(
    twin='HFpEF', state='rest', pvd=False, afib=False,
    shunt_mm=0.0, shunt_cd=0.7,
    mr='none', tr='none', mr_eroa=None, tr_eroa=None, lesion_comp=True, lesion_gain=20.0,
    bat=0.0, padn=False, sota=0.0,
    chronic=True, gain=None, pvr_rise=None,
    hr=None, lv_ees=1.0, lv_stiff=1.0, rv_ees=1.0, rv_stiff=1.0, la_stiff=1.0, ra_stiff=1.0,
    svr=1.0, pvr=1.0, cpa=1.0, csv=1.0, dsbv=0.0,
    pericardium=True, septum=0.0,
    **ASSUMPTIONS)

# Patient-level keys: changing only therapy keys reuses the cached patient baseline.
PATIENT_KEYS = ('twin', 'afib', 'mr', 'tr', 'mr_eroa', 'tr_eroa', 'lesion_comp', 'lesion_gain', 'hr', 'lv_ees',
                'lv_stiff', 'rv_ees', 'rv_stiff', 'la_stiff', 'ra_stiff', 'svr', 'pvr', 'cpa', 'csv',
                'dsbv', 'pericardium', 'septum')
_cache = {}


def _scale(ch, ees, stiff):
    E, V0, A, B = ch
    return (E * ees, V0, A, B * stiff)


def eroa(s, valve):
    v = s[valve + '_eroa']
    return float(v) if v is not None else (MR_EROA if valve == 'mr' else TR_EROA)[s[valve]]


def build_patient(s):
    """Twin x patient modifiers, without lesions (valves, AF)."""
    p = copy.deepcopy(TWINS[s['twin']])
    if s['hr']:
        p['HR'] = float(s['hr'])
    p['LV'] = _scale(p['LV'], s['lv_ees'], s['lv_stiff'])
    p['RV'] = _scale(p['RV'], s['rv_ees'], s['rv_stiff'])
    p['LA'] = _scale(p['LA'], 1.0, s['la_stiff'])
    p['RA'] = _scale(p['RA'], 1.0, s['ra_stiff'])
    p['SVR'] *= s['svr']
    p['PVR'] *= s['pvr']
    p['Cpa'] *= s['cpa']
    p['Csv'] *= s['csv']
    p['SBV'] += s['dsbv']
    return p


def patient_baseline(s, log=print):
    """Untreated patient at rest: returns (params, metrics, state, notes). Cached."""
    key = tuple(s[k] for k in PATIENT_KEYS)
    if key in _cache:
        log('Patient baseline: reused from cache')
        return copy.deepcopy(_cache[key])
    notes = []
    p = build_patient(s)
    p['MR'], p['TR'] = eroa(s, 'mr'), eroa(s, 'tr')
    p['afib'] = bool(s['afib'])
    lesion = p['MR'] > 0 or p['TR'] > 0 or p['afib']
    log('Patient baseline: simulating...')
    if lesion and s['lesion_comp']:
        ref, yref = simulate(build_patient(s))
        log('Chronic compensation of valve disease / AF: solving retained volume...')
        g = float(s['lesion_gain'])
        dv, r, _ = solve_volume_arm(p, g, ref['MAP'], yref, 0.0, hi=VOLUME_CAP)
        p['SBV'] += dv
        notes.append(f"Lesion compensation (gain {g:g} mL/mmHg): +{dv:.0f} mL stressed volume; MAP "
                     f"{r['MAP']:.0f} vs {ref['MAP']:.0f} mmHg without the lesion.")
        if dv > 0.98 * VOLUME_CAP:
            notes.append(f"WARNING: lesion compensation reached the {VOLUME_CAP:.0f} mL cap; the target was not met.")
    if s['pericardium']:
        p, y0 = with_pericardium(p)
    else:
        y0 = None
    b, yb = simulate(p, y0=y0)
    if s['septum'] > 0:
        p = with_septum(p, yb, float(s['septum']))
    out = (p, b, yb, notes)
    _cache[key] = copy.deepcopy(out)
    return out


def apply_therapy(p, s, b, yb, log=print):
    """Treated resting params and the volume retained by the reflex."""
    fit = FIT[s['twin']]
    gain = fit['gain'] if s['gain'] is None else float(s['gain'])
    rise0 = fit['pvr_rise'] if s['pvr_rise'] is None else float(s['pvr_rise'])
    d, fb, fp, fs = s['shunt_mm'], s['bat'], (1.0 if s['padn'] else 0.0), s['sota']
    chronic = s['chronic'] and d > 0
    warn = []
    q = copy.deepcopy(p)
    rise = rise0 * (1 - fb) * (1 - fp) if chronic else 0.0
    q['PVR'] *= (1 + rise) * (1 - s['padn_pvr'] * fp) * (1 - s['sota_pvr'] * fs)
    dv = 0.0
    if chronic and gain != 0:
        log('Shunt volume arm: solving retained volume...')
        dv_full, _, _ = solve_volume_arm(q, gain, b['MAP'], yb, d, hi=VOLUME_CAP)
        dv = (1 - fb) * dv_full
        if dv_full > 0.98 * VOLUME_CAP:
            warn.append(f"WARNING: shunt volume arm reached the {VOLUME_CAP:.0f} mL cap; MAP not restored.")
    q['SBV'] += dv - s['bat_sbv'] * fb * p['SBV']
    q['SVR'] *= 1 - s['bat_svr'] * fb
    q['HR'] *= 1 - s['bat_hr'] * fb
    return q, dict(dV=dv, pvr_rise=rise, gain=gain, warnings=warn)


def exercise_state(p, rest, s, treated):
    """Exercise params from the untreated patient p and resting params `rest`."""
    q = copy.deepcopy(p)
    q.pop('septum', None)                      # septal term is only valid at resting HR
    ex = exercise(q, s['twin'], s['pvd'])
    fp = (1.0 if s['padn'] else 0.0) if treated else 0.0
    sp = 1 - fp
    if s['pvd']:
        ex['PVR'] = rest['PVR'] * (0.85 + 0.55 * sp)
        ex['Cpa'] = p['Cpa'] * (1.0 - 0.4 * sp)
    else:
        ex['PVR'] = rest['PVR'] * 0.85
    if treated:
        ex['SBV'] += rest['SBV'] - p['SBV']        # retained volume and BAT volume change
        ex['SVR'] *= rest['SVR'] / p['SVR']
        ex['HR'] *= rest['HR'] / p['HR']
    return ex


def run_scenario(settings, log=print):
    """Returns dict(base=metrics, scen=metrics, info=..., notes=[...]); metrics include traces."""
    s = dict(DEFAULTS, **settings)
    model.SHUNT_CD = float(s['shunt_cd'])
    p, b, yb, notes = patient_baseline(s, log)
    notes = list(notes)
    rest, info = apply_therapy(p, s, b, yb, log)
    if s['state'] == 'exercise':
        if s['septum'] > 0:
            notes.append('Septal interaction is switched off in exercise (it is referenced to the resting beat).')
        base_p = exercise_state(p, p, s, treated=False)
        scen_p = exercise_state(p, rest, s, treated=True)
    else:
        base_p, scen_p = p, rest
    log('Simulating untreated reference...')
    base, yref = simulate(base_p, y0=yb, trace=True)
    log('Simulating scenario...')
    scen, _ = simulate(scen_p, s['shunt_mm'], y0=yref, trace=True)
    for m, q in ((base, base_p), (scen, scen_p)):
        m['PVR_WU'] = q['PVR'] * 1000 / 60          # mmHg*s/mL -> Wood units
        m['SVR_WU'] = q['SVR'] * 1000 / 60
        m['dV'] = q['SBV'] - p['SBV']
    info.update(MR_EROA=p.get('MR', 0.0), TR_EROA=p.get('TR', 0.0))
    notes += info.pop('warnings')
    if s['shunt_mm'] > 0 and not s['chronic']:
        notes.append('Acute shunt: no reflex volume retention and no post-shunt PVR rise.')
    return dict(base=base, scen=scen, info=info, notes=notes, settings=s)


def classify(valve, rvol, rf):
    """Guideline severity class from regurgitant volume (mL) and fraction (%)."""
    if rvol < 1:
        return 'none'
    if valve == 'MR':
        by_v = 'severe' if rvol >= 60 else 'moderate' if rvol >= 30 else 'mild'
        by_f = 'severe' if rf >= 50 else 'moderate' if rf >= 30 else 'mild'
    else:
        by_v = 'severe' if rvol >= 45 else 'moderate' if rvol >= 30 else 'mild'
        by_f = by_v
    order = ('mild', 'moderate', 'severe')
    return max(by_v, by_f, key=order.index)
