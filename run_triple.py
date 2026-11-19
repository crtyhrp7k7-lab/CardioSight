"""Shunt with baroreflex activation (BAT) and pulmonary artery denervation (PADN) together.

Usage: python run_triple.py [HFpEF|HFrEF] [shunt_diameter_mm]

Same assumed representations as run_bat.py and run_padn.py, strengths fb and fp (0 to 1):
  BAT   retained volume and post-shunt PVR rise x (1 - fb); SVR -10%, HR -5%, stressed volume -4% at fb = 1
  PADN  post-shunt PVR rise and exercise PVD change x (1 - fp); resting PVR -10% at fp = 1
All magnitudes are assumptions.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, solve_volume_arm, exercise

INF = float('inf')
FIT = {'HFrEF': dict(gain=20, pvr_rise=0.0), 'HFpEF': dict(gain=INF, pvr_rise=0.5)}
OUT = ('MAP', 'CO', 'PCWP', 'RAP', 'PAs', 'mPAP', 'RVEDV', 'LAmax', 'QpQs')


def build(p, kind, yb, map_set, d, fb, fp):
    fit = FIT[kind]
    rest = copy.deepcopy(p)
    rise = fit['pvr_rise'] * (1 - fb) * (1 - fp) if d > 0 else 0.0
    rest['PVR'] *= (1 + rise) * (1 - 0.10 * fp)
    dv = 0.0
    if d > 0:
        dv_full, _, _ = solve_volume_arm(rest, fit['gain'], map_set, yb, d)
        dv = (1 - fb) * dv_full
    rest['SBV'] += dv - 0.04 * fb * p['SBV']
    rest['SVR'] *= 1 - 0.10 * fb
    rest['HR'] *= 1 - 0.05 * fb
    ex = exercise(p, kind, True)
    s = 1 - fp
    ex['PVR'] = rest['PVR'] * (0.85 + 0.55 * s)
    ex['Cpa'] = p['Cpa'] * (1.0 - 0.4 * s)
    ex['SBV'] += dv - 0.04 * fb * p['SBV']
    ex['SVR'] *= 1 - 0.10 * fb
    ex['HR'] *= 1 - 0.05 * fb
    return rest, ex, dv


if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'HFpEF'
    d_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    p, y0 = with_pericardium(TWINS[kind])
    b, yb = simulate(p, y0=y0)
    arms = [('no therapy', 0.0, 0.0, 0.0), ('shunt alone', d_mm, 0.0, 0.0),
            ('shunt + BAT 1.0', d_mm, 1.0, 0.0), ('shunt + PADN 1.0', d_mm, 0.0, 1.0),
            ('shunt + BAT 0.5 + PADN 0.5', d_mm, 0.5, 0.5), ('shunt + BAT 1.0 + PADN 1.0', d_mm, 1.0, 1.0),
            ('shunt + BAT 0.5 + PADN 1.0', d_mm, 0.5, 1.0), ('BAT 1.0 + PADN 1.0, no shunt', 0.0, 1.0, 1.0)]
    built = [(n, d) + build(p, kind, yb, b['MAP'], d, fb, fp) for n, d, fb, fp in arms]
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
    (res / f'triple_{kind}.json').write_text(json.dumps(out, indent=1))
