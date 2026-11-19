"""Why does the HFpEF left atrium enlarge? Two candidate mechanisms.

Usage: python run_la_volume.py [HFpEF|HFrEF] [shunt_diameter_mm]
Reproduces the "Left atrial volume" tables.

1. Retention beyond arterial-pressure restoration: stressed volume is added in fixed
   steps, as a flow-defending (renal) loop with a ceiling would do.
2. Diastolic ventricular interaction: a fraction beta of the rise in RV passive
   pressure above baseline is transmitted to the LV (and 0.1 of the reverse).
Resting state, pericardium on. HFpEF uses resting PVR +50% after shunting, HFrEF none.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, with_septum, solve_volume_arm

OUT = ('PCWP', 'RAP', 'PAs', 'MAP', 'CO', 'LVEDV', 'LAmax', 'RVEDV', 'RAmax', 'QpQs', 'LVEDP')
SET = {'HFpEF': dict(pvr=1.5, steps=['map', 400, 600, 800]), 'HFrEF': dict(pvr=1.0, steps=[83, 343])}
BETAS = (0.0, 0.3, 0.5)

if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'HFpEF'
    d_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    p, y0 = with_pericardium(TWINS[kind])
    b, yb = simulate(p, y0=y0)
    out = dict(base={k: b[k] for k in OUT}, cases=[])
    print(f"===== {kind}: resting, shunt minus no shunt, PVR x{SET[kind]['pvr']}")
    print(" beta   dV | dPCWP dLVEDP dRAP  dPAs  dMAP | LVEDV%  LA%   RV%   RA% |   CO QpQs", flush=True)
    for beta in BETAS:
        q0 = with_septum(p, yb, beta) if beta > 0 else copy.deepcopy(p)
        chk, _ = simulate(q0, y0=yb)
        assert abs(chk['PCWP'] - b['PCWP']) < 0.05, 'baseline changed by septal term'
        q0['PVR'] *= SET[kind]['pvr']
        for step in SET[kind]['steps']:
            if step == 'map':
                dv, s, _ = solve_volume_arm(q0, float('inf'), b['MAP'], yb, d_mm)
            else:
                dv = float(step)
                q = copy.deepcopy(q0)
                q['SBV'] += dv
                s, _ = simulate(q, d_mm, y0=yb)
            d = {k: s[k] - b[k] for k in OUT}
            pct = {k: 100 * d[k] / b[k] for k in ('LVEDV', 'LAmax', 'RVEDV', 'RAmax')}
            out['cases'].append(dict(beta=beta, dV=dv, change=d, percent=pct))
            print(f"{beta:5.1f} {dv:4.0f} | {d['PCWP']:+5.1f} {d['LVEDP']:+6.1f} {d['RAP']:+4.1f} {d['PAs']:+5.1f} {d['MAP']:+5.1f} |"
                  f" {pct['LVEDV']:+5.1f} {pct['LAmax']:+5.1f} {pct['RVEDV']:+5.1f} {pct['RAmax']:+5.1f} | {s['CO']:.2f} {s['QpQs']:.2f}", flush=True)
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / f'la_volume_{kind}.json').write_text(json.dumps(out, indent=1))
