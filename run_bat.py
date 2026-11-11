"""Predicted effect of combining the shunt with baroreflex activation therapy (BAT).

Usage: python run_bat.py [shunt_diameter_mm]     (default 6)
Reproduces the "Predicted effect of adding baroreflex activation" tables.

BAT is not modeled mechanistically. It is represented by a strength f (0 to 1):
  reflex attenuation   the volume the reflex recruits after shunting, and the post-shunt
                       rise in resting PVR, are both scaled by (1 - f)
  direct effects       SVR -10%*f, heart rate -5%*f, stressed volume -4%*f
The 'fixed PVD' rows keep the full PVR rise, as if it were structural and not neural.
Chronic shunt-alone settings are the best fits from run_echo_matrix.py:
HFrEF gain 20 mL/mmHg, no PVR rise; HFpEF full arterial-pressure restoration, PVR +50%.
All of these magnitudes are assumptions.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, solve_volume_arm, exercise

INF = float('inf')
FIT = {'HFrEF': dict(gain=20, pvr_rise=0.0), 'HFpEF': dict(gain=INF, pvr_rise=0.5)}
DIRECT = dict(SVR=0.10, HR=0.05, SBV=0.04)
OUT = ('MAP', 'CO', 'PCWP', 'RAP', 'PAs', 'mPAP', 'RVEDV', 'LAmax', 'QpQs')


def apply_bat(p, f, sbv0):
    q = copy.deepcopy(p)
    q['SVR'] *= 1 - DIRECT['SVR'] * f
    q['HR'] *= 1 - DIRECT['HR'] * f
    q['SBV'] -= DIRECT['SBV'] * f * sbv0
    return q


def arm(p, kind, yb, map_set, d_mm, f, fixed_pvd=False):
    """Return (rest params, recruited volume) for one therapy arm."""
    fit = FIT[kind]
    q = copy.deepcopy(p)
    dv = 0.0
    if d_mm > 0:
        rise = fit['pvr_rise'] * (1.0 if fixed_pvd else 1 - f)
        q['PVR'] *= 1 + rise
        dv_full, _, _ = solve_volume_arm(q, fit['gain'], map_set, yb, d_mm)
        dv = (1 - f) * dv_full
        q['SBV'] += dv
    return apply_bat(q, f, p['SBV']), dv


if __name__ == '__main__':
    d_mm = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    out = {}
    for kind, p0 in TWINS.items():
        p, y0 = with_pericardium(p0)
        b, yb = simulate(p, y0=y0)
        arms = [('no therapy', 0.0, 0.0, False), ('shunt alone', d_mm, 0.0, False),
                ('BAT alone f=0.5', 0.0, 0.5, False), ('BAT alone f=1.0', 0.0, 1.0, False),
                ('shunt + BAT f=0.5', d_mm, 0.5, False), ('shunt + BAT f=1.0', d_mm, 1.0, False)]
        if FIT[kind]['pvr_rise'] > 0:
            arms += [('shunt + BAT f=0.5, fixed PVD', d_mm, 0.5, True),
                     ('shunt + BAT f=1.0, fixed PVD', d_mm, 1.0, True)]
        out[kind] = {}
        print(f"\n===== {kind} =====")
        for state in ('rest', 'exercise + PVD'):
            print(f"-- {state}")
            print(f"{'arm':30s}   dV |   MAP    CO |  PCWP   RAP   PAs  mPAP | RVEDV% QpQs")
            ref = None
            for name, d, f, fixed in arms:
                q, dv = arm(p, kind, yb, b['MAP'], d, f, fixed)
                if state != 'rest':
                    hr_scale = q['HR'] / p['HR']
                    extra = q['SBV'] - p['SBV']
                    svr_scale, pvr_scale = q['SVR'] / p['SVR'], q['PVR'] / p['PVR']
                    q = exercise(p, kind, True)
                    q['HR'] *= hr_scale
                    q['SVR'] *= svr_scale
                    q['PVR'] *= pvr_scale
                    q['SBV'] += extra
                r, _ = simulate(q, d, y0=yb)
                if ref is None:
                    ref = r
                    print(f"{name:30s} {dv:4.0f} | {r['MAP']:5.1f} {r['CO']:5.2f} | {r['PCWP']:5.1f} {r['RAP']:5.1f} "
                          f"{r['PAs']:5.1f} {r['mPAP']:5.1f} | {r['RVEDV']:5.0f}mL {r['QpQs']:.2f}")
                else:
                    print(f"{name:30s} {dv:4.0f} | {r['MAP'] - ref['MAP']:+5.1f} {r['CO'] - ref['CO']:+5.2f} | "
                          f"{r['PCWP'] - ref['PCWP']:+5.1f} {r['RAP'] - ref['RAP']:+5.1f} {r['PAs'] - ref['PAs']:+5.1f} "
                          f"{r['mPAP'] - ref['mPAP']:+5.1f} | {100 * (r['RVEDV'] / ref['RVEDV'] - 1):+6.1f} {r['QpQs']:.2f}")
                out[kind].setdefault(state, {})[name] = dict(dV=dv, **{k: r[k] for k in OUT})
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / 'bat.json').write_text(json.dumps(out, indent=1))
