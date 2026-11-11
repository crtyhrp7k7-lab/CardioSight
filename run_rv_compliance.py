"""Right-heart compliance in isolation.

Usage: python run_rv_compliance.py [shunt_diameter_mm]     (default 6)
Reproduces the "Right-heart compliance in isolation" table.

The passive stiffness exponent B of the RV and RA is scaled, and total stressed
volume re-tuned so every variant starts from the same no-shunt wedge pressure.
Changes are shunt minus no shunt, acute, with no reflex.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, ed_stiffness

SCALES = (0.8, 1.0, 1.15, 1.3)
OUT = ('PCWP', 'RAP', 'PAs', 'mPAP', 'CO', 'MAP', 'LVEDV', 'LAmax', 'RVEDV', 'RAmax', 'QpQs')

if __name__ == '__main__':
    d_mm = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    out = {}
    print("twin  scale |  SBV  PCWP   RAP   PAs RVEDV dP/dV | dRVEDV dRAmax  dRAP dPCWP  dPAs dLVEDV QpQs  dCO%")
    for kind, p0 in TWINS.items():
        target, _ = simulate(p0)
        target = target['PCWP']
        out[kind] = {}
        for s in SCALES:
            q0 = copy.deepcopy(p0)
            for ch in ('RV', 'RA'):
                E, V0, A, B = q0[ch]
                q0[ch] = (E, V0, A, B * s)
            lo, hi, y = p0['SBV'] - 500, p0['SBV'] + 900, None
            for _ in range(9):                       # bisection on stressed volume
                mid = 0.5 * (lo + hi)
                q = copy.deepcopy(q0)
                q['SBV'] = mid
                b, y = simulate(q, y0=y)
                if b['PCWP'] < target:
                    lo = mid
                else:
                    hi = mid
            q['peri'] = (b['Vheart'], 0.08 * b['Vheart'], 3.0)
            b, yb = simulate(q, y0=y)
            sh, _ = simulate(q, d_mm, y0=yb)
            d = {k: sh[k] - b[k] for k in OUT}
            st = ed_stiffness(q['RV'], b['RVEDV'])
            out[kind][str(s)] = dict(SBV=mid, base={k: b[k] for k in OUT}, rv_stiffness=st, change=d, QpQs=sh['QpQs'])
            print(f"{kind} {s:5.2f} | {mid:5.0f} {b['PCWP']:5.1f} {b['RAP']:5.1f} {b['PAs']:5.1f} {b['RVEDV']:5.0f} {st:.3f} |"
                  f" {d['RVEDV']:+6.1f} {d['RAmax']:+6.1f} {d['RAP']:+5.1f} {d['PCWP']:+5.1f} {d['PAs']:+5.1f} {d['LVEDV']:+6.1f}"
                  f" {sh['QpQs']:.2f} {100 * d['CO'] / b['CO']:+5.1f}")
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / 'rv_compliance.json').write_text(json.dumps(out, indent=1))
