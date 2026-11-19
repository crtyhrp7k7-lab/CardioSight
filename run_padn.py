"""Predicted effect of combining the shunt with pulmonary artery denervation (PADN).

Usage: python run_padn.py [HFpEF|HFrEF] [shunt_diameter_mm]
Reproduces the "Predicted effect of adding pulmonary artery denervation" tables.

PADN is not modeled mechanistically. It is represented by a strength f (0 to 1):
  pulmonary reflex   the post-shunt rise in resting PVR, and the exercise PVD change
                     (PVR +40%, PA compliance -40% instead of PVR -15%), scale by (1 - f)
  direct effect      resting PVR -10% * f
The volume arm is NOT touched: retention still restores arterial pressure (HFpEF) or
follows gain 20 mL/mmHg (HFrEF). 'fixed PVD' keeps the PVR rise and exercise PVD in
full, as if structural; only the direct effect remains. All magnitudes are assumptions.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, solve_volume_arm, exercise

INF = float('inf')
FIT = {'HFrEF': dict(gain=20, pvr_rise=0.0), 'HFpEF': dict(gain=INF, pvr_rise=0.5)}
DIRECT_PVR = 0.10
OUT = ('MAP', 'CO', 'PCWP', 'RAP', 'PAs', 'mPAP', 'RVEDV', 'LAmax', 'QpQs')


def build(p, kind, yb, map_set, d, f, fixed):
    fit = FIT[kind]
    s = 1.0 if fixed else 1.0 - f                    # remaining pulmonary reflex
    rest = copy.deepcopy(p)
    rest['PVR'] *= (1 + (fit['pvr_rise'] * s if d > 0 else 0.0)) * (1 - DIRECT_PVR * f)
    dv = 0.0
    if d > 0:
        dv, _, _ = solve_volume_arm(rest, fit['gain'], map_set, yb, d)
        rest['SBV'] += dv
    ex = exercise(p, kind, True)
    ex['PVR'] = rest['PVR'] * (0.85 + 0.55 * s)
    ex['Cpa'] = p['Cpa'] * (1.0 - 0.4 * s)
    ex['SBV'] += dv
    return rest, ex, dv


if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'HFpEF'
    d_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    p, y0 = with_pericardium(TWINS[kind])
    b, yb = simulate(p, y0=y0)
    arms = [('no therapy', 0.0, 0.0, False), ('shunt alone', d_mm, 0.0, False),
            ('PADN alone f=0.5', 0.0, 0.5, False), ('PADN alone f=1.0', 0.0, 1.0, False),
            ('shunt + PADN f=0.5', d_mm, 0.5, False), ('shunt + PADN f=1.0', d_mm, 1.0, False),
            ('shunt + PADN f=1.0, fixed PVD', d_mm, 1.0, True)]
    built = [(n, d) + build(p, kind, yb, b['MAP'], d, f, fx) for n, d, f, fx in arms]
    out = {}
    print(f"===== {kind} =====")
    for state, idx in (('rest', 2), ('exercise + PVD', 3)):
        print(f"-- {state}")
        print(f"{'arm':30s}   dV |   MAP    CO |  PCWP   RAP   PAs  mPAP | RVEDV%  LA%  QpQs", flush=True)
        ref = None
        for row in built:
            name, d, dv = row[0], row[1], row[4]
            r, _ = simulate(row[idx], d, y0=yb)
            if ref is None:
                ref = r
                print(f"{name:30s} {dv:4.0f} | {r['MAP']:5.1f} {r['CO']:5.2f} | {r['PCWP']:5.1f} {r['RAP']:5.1f} "
                      f"{r['PAs']:5.1f} {r['mPAP']:5.1f} | {r['RVEDV']:5.0f}mL {r['LAmax']:4.0f}mL {r['QpQs']:.2f}", flush=True)
            else:
                print(f"{name:30s} {dv:4.0f} | {r['MAP'] - ref['MAP']:+5.1f} {r['CO'] - ref['CO']:+5.2f} | "
                      f"{r['PCWP'] - ref['PCWP']:+5.1f} {r['RAP'] - ref['RAP']:+5.1f} {r['PAs'] - ref['PAs']:+5.1f} "
                      f"{r['mPAP'] - ref['mPAP']:+5.1f} | {100 * (r['RVEDV'] / ref['RVEDV'] - 1):+6.1f} "
                      f"{100 * (r['LAmax'] / ref['LAmax'] - 1):+5.1f}  {r['QpQs']:.2f}", flush=True)
            out.setdefault(state, {})[name] = dict(dV=dv, **{k: r[k] for k in OUT})
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / f'padn_{kind}.json').write_text(json.dumps(out, indent=1))
