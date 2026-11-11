"""Exercise, pulmonary vascular disease (PVD) and chronic volume retention.

Usage: python run_scenarios.py [shunt_diameter_mm]     (default 6)
Reproduces the "Results 2" table. "Retention" adds the stressed volume that
restores pre-shunt resting mean arterial pressure (infinite volume-arm gain).
"""
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, exercise, solve_volume_arm

KEYS = ['CO', 'QpQs', 'PCWP', 'RAP', 'mPAP', 'MAP', 'LVEDV', 'RVEDV', 'RVEF', 'Pperi', 'SBV']


def line(tag, r):
    print(f"{tag:36s}" + ' '.join(f"{r[k]:7.2f}" for k in KEYS))


if __name__ == '__main__':
    d_mm = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    out = {}
    for kind, p0 in TWINS.items():
        print(f"\n===== {kind} =====\n{'':36s}" + ' '.join(f"{k:>7s}" for k in KEYS))
        p, y0 = with_pericardium(p0)
        R = {}
        R['rest_base'], yb = simulate(p, y0=y0)
        line('rest   no shunt', R['rest_base'])
        R['rest_shunt'], ys = simulate(p, d_mm, y0=yb)
        line('rest   shunt, acute', R['rest_shunt'])
        dV, R['rest_shunt_ret'], p_ret = solve_volume_arm(p, float('inf'), R['rest_base']['MAP'], ys, d_mm)
        line(f'rest   shunt + retention ({dV:+.0f} mL)', R['rest_shunt_ret'])
        R['retained_mL'] = dV
        for pvd in (False, True):
            tag = 'exPVD' if pvd else 'ex'
            R[tag + '_base'], ye = simulate(exercise(p, kind, pvd), y0=yb)
            line(f'{tag:6s} no shunt', R[tag + '_base'])
            R[tag + '_shunt'], _ = simulate(exercise(p, kind, pvd), d_mm, y0=ye)
            line(f'{tag:6s} shunt, acute', R[tag + '_shunt'])
            R[tag + '_shunt_ret'], _ = simulate(exercise(p_ret, kind, pvd), d_mm, y0=ye)
            line(f'{tag:6s} shunt + retention', R[tag + '_shunt_ret'])
        out[kind] = R
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / 'scenarios.json').write_text(json.dumps(out, indent=1))
