"""Resting matrix for comparison with 12-month echocardiographic findings.

Usage: python run_echo_matrix.py [shunt_diameter_mm]     (default 6)
Reproduces "Which settings match the trial's echocardiograms" and the
operating-stiffness rows of the Methods table.

Each case sets a volume-arm gain (mL/mmHg; inf restores arterial pressure) and a
resting PVR scale, and reports shunt minus no-shunt changes in echo-comparable outputs.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, solve_volume_arm, ed_stiffness

INF = float('inf')
OUT = ('PCWP', 'RAP', 'PAs', 'mPAP', 'CO', 'MAP', 'LVEDV', 'LVESV', 'LAmax', 'RVEDV', 'RAmax', 'QpQs')
CASES = {'HFrEF': [(0, 1.0), (20, 1.0), (INF, 1.0), (INF, 1.3)],
         'HFpEF': [(0, 1.0), (0, 1.3), (INF, 1.0), (INF, 1.15), (INF, 1.3), (INF, 1.5)]}

if __name__ == '__main__':
    d_mm = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    out = {}
    for kind, p0 in TWINS.items():
        p, y0 = with_pericardium(p0)
        b, yb = simulate(p, y0=y0)
        lv, rv = ed_stiffness(p['LV'], b['LVEDV']), ed_stiffness(p['RV'], b['RVEDV'])
        print(f"\n===== {kind}: end-diastolic stiffness LV {lv:.3f}, RV {rv:.3f} mmHg/mL")
        print(" gain PVRx |   dV | dPCWP dRAP  dPAs dmPAP | LVEDV%  LA%   RV%   RA% |   CO QpQs")
        out[kind] = dict(base={k: b[k] for k in OUT}, stiffness=dict(LV=lv, RV=rv), cases=[])
        for gain, scale in CASES[kind]:
            q = copy.deepcopy(p)
            q['PVR'] *= scale
            dv, s, _ = solve_volume_arm(q, gain, b['MAP'], yb, d_mm)
            d = {k: s[k] - b[k] for k in OUT}
            pct = {k: 100 * d[k] / b[k] for k in ('LVEDV', 'LAmax', 'RVEDV', 'RAmax')}
            out[kind]['cases'].append(dict(gain=str(gain), pvr_scale=scale, dV=dv, change=d, percent=pct))
            print(f"{str(gain):>5s} {scale:4.2f} | {dv:4.0f} | {d['PCWP']:+5.1f} {d['RAP']:+4.1f} {d['PAs']:+5.1f} {d['mPAP']:+5.1f} |"
                  f" {pct['LVEDV']:+5.1f} {pct['LAmax']:+5.1f} {pct['RVEDV']:+5.1f} {pct['RAmax']:+5.1f} | {s['CO']:.2f} {s['QpQs']:.2f}")
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / 'echo_matrix.json').write_text(json.dumps(out, indent=1))
