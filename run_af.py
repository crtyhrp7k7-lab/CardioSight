"""Loss of atrial contraction (atrial fibrillation) and left atrial volume.

Usage: python run_af.py [HFpEF|HFrEF] [shunt_diameter_mm]
Reproduces the "Atrial fibrillation and left atrial volume" table.

AF is represented only as absent atrial contraction in both atria, at the same
regular heart rate. Shunt cases use the chronic best-fit settings (HFpEF: PVR +50%,
arterial pressure restored; HFrEF: gain 20 mL/mmHg). AF cases without a shunt are
shown with and without the same volume arm. Changes are against sinus rhythm, no shunt.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, solve_volume_arm

FIT = {'HFpEF': dict(gain=float('inf'), pvr=1.5), 'HFrEF': dict(gain=20, pvr=1.0)}
OUT = ('PCWP', 'LAv', 'RAP', 'PAs', 'MAP', 'CO', 'LAmax', 'RAmax', 'RVEDV', 'LVEDV', 'QpQs')

if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'HFpEF'
    d_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    fit = FIT[kind]
    p, y0 = with_pericardium(TWINS[kind])
    b, yb = simulate(p, y0=y0)
    cases = [('sinus, no shunt', False, 0.0, False), ('AF, no shunt, no retention', True, 0.0, False),
             ('AF, no shunt, volume arm', True, 0.0, True), ('sinus, shunt', False, d_mm, True),
             ('AF, shunt', True, d_mm, True)]
    out = {}
    print(f"===== {kind}: change against sinus rhythm without shunt")
    print(f"{'case':28s}   dV | dPCWP  dRAP  dPAs  dMAP    CO | LAmax%  RAmax%   RV%  LVEDV% QpQs", flush=True)
    for name, af, d, arm in cases:
        q = copy.deepcopy(p)
        q['afib'] = af
        if d > 0:
            q['PVR'] *= fit['pvr']
        if arm:
            dv, s, _ = solve_volume_arm(q, fit['gain'], b['MAP'], yb, d)
        else:
            dv = 0.0
            s, _ = simulate(q, d, y0=yb)
        pc = lambda k: 100 * (s[k] / b[k] - 1)
        out[name] = dict(dV=dv, **{k: s[k] for k in OUT})
        print(f"{name:28s} {dv:4.0f} | {s['PCWP']-b['PCWP']:+5.1f} {s['RAP']-b['RAP']:+5.1f} {s['PAs']-b['PAs']:+5.1f} "
              f"{s['MAP']-b['MAP']:+5.1f} {s['CO']:5.2f} | {pc('LAmax'):+6.1f} {pc('RAmax'):+7.1f} {pc('RVEDV'):+5.1f} {pc('LVEDV'):+7.1f} {s['QpQs']:.2f}", flush=True)
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / f'af_{kind}.json').write_text(json.dumps(out, indent=1))
