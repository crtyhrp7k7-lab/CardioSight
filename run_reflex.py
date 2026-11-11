"""Reflex arms after shunt opening: cardiac arm versus volume arm.

Usage: python run_reflex.py [shunt_diameter_mm]     (default 6)
Reproduces the "Cardiac arm against volume arm" tables.

Volume arm: dV = gain * (MAP_set - MAP), gain in mL/mmHg. The response to added
stressed volume is computed on a grid and the fixed point found by interpolation.
Cardiac arm: heart rate and LV/RV Ees raised 10%, no added volume.
"""
import copy
import json
import sys
from pathlib import Path
from model import TWINS, simulate, with_pericardium, exercise

GRID = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450]       # added stressed volume, mL
GAINS = [0, 10, 20, 40, 80, 160, float('inf')]
M = ('MAP', 'PCWP', 'RAP', 'CO', 'mPAP', 'QpQs')


def interp(xs, ys, x):
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            f = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + f * (ys[i + 1] - ys[i])
    return ys[-1] if x > xs[-1] else ys[0]


def fixed_point(curve, gain, map_set):
    lo, hi = 0.0, GRID[-1]
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        deficit = max(map_set - interp(GRID, curve['MAP'], mid), 0.0)
        g = (1e9 if gain == float('inf') else gain) * deficit - mid
        if g > 0:
            lo = mid
        else:
            hi = mid
    return mid


if __name__ == '__main__':
    d_mm = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    out = {}
    for kind, p0 in TWINS.items():
        p, y0 = with_pericardium(p0)
        res = {}
        states = {'rest': p, 'ex': exercise(p, kind, False), 'exPVD': exercise(p, kind, True)}
        for st, ps in states.items():
            base, y = simulate(ps, y0=y0)
            curve = {m: [] for m in M}
            for dv in GRID:
                q = copy.deepcopy(ps)
                q['SBV'] += dv
                r, y = simulate(q, d_mm, y0=y)
                for m in M:
                    curve[m].append(r[m])
            res[st] = dict(base={m: base[m] for m in M}, curve=curve)

        q = copy.deepcopy(p)
        q['HR'] *= 1.10
        for ch in ('LV', 'RV'):
            E, V0, A, B = q[ch]
            q[ch] = (E * 1.10, V0, A, B)
        rc, _ = simulate(q, d_mm, y0=y0)
        res['cardiac_arm'] = {m: rc[m] for m in M}
        out[kind] = res

        b = res['rest']['base']
        print(f"\n===== {kind}: no-shunt rest MAP {b['MAP']:.1f}, PCWP {b['PCWP']:.1f}, RAP {b['RAP']:.1f}")
        print(f"cardiac arm only (HR and Ees +10%): MAP {rc['MAP']:.1f}  CO {rc['CO']:.2f}  PCWP {rc['PCWP']:.1f}  RAP {rc['RAP']:.1f}")
        print(" gain    dV | rest dPCWP  dRAP    CO | ex dPCWP  dRAP | exPVD dPCWP  dRAP")
        for g in GAINS:
            dv = fixed_point(res['rest']['curve'], g, b['MAP'])
            row = []
            for st in ('rest', 'ex', 'exPVD'):
                c, bb = res[st]['curve'], res[st]['base']
                row.append((interp(GRID, c['PCWP'], dv) - bb['PCWP'], interp(GRID, c['RAP'], dv) - bb['RAP'],
                            interp(GRID, c['CO'], dv)))
            print(f"{g:5.0f} {dv:5.0f} | {row[0][0]:+10.1f} {row[0][1]:+5.1f} {row[0][2]:5.2f} |"
                  f" {row[1][0]:+8.1f} {row[1][1]:+5.1f} | {row[2][0]:+11.1f} {row[2][1]:+5.1f}")
        c = res['rest']['curve']
        print("per 100 mL added (rest, 0-200 mL): PCWP %+.2f  RAP %+.2f  MAP %+.2f mmHg"
              % tuple((c[m][4] - c[m][0]) / 2 for m in ('PCWP', 'RAP', 'MAP')))
    resdir = Path(__file__).parent / 'results'
    resdir.mkdir(exist_ok=True)
    (resdir / 'reflex.json').write_text(json.dumps(out, indent=1))
