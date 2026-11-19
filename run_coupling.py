"""Ventriculo-arterial coupling (Ees/Ea) for the triple-therapy arms.

Usage: python run_coupling.py [HFpEF|HFrEF] [shunt_diameter_mm]

RV coupling = RV Ees / RV Ea, with Ea = RV end-systolic pressure / RV stroke volume.
Lower = more uncoupled (a common clinical threshold for RV-PA uncoupling is
about 0.7 by pressure-volume methods). Arms and assumptions as in run_triple.py.
"""
import sys
from model import TWINS, simulate, with_pericardium
from run_triple import build

if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'HFpEF'
    d = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    p, y0 = with_pericardium(TWINS[kind])
    b, yb = simulate(p, y0=y0)
    arms = [('no therapy', 0.0, 0, 0), ('shunt alone', d, 0, 0), ('shunt + BAT 1.0', d, 1, 0),
            ('shunt + PADN 1.0', d, 0, 1), ('shunt + BAT 0.5 + PADN 0.5', d, .5, .5),
            ('shunt + BAT 1.0 + PADN 1.0', d, 1, 1), ('BAT 1.0 + PADN 1.0, no shunt', 0.0, 1, 1)]
    built = [(n, dd) + build(p, kind, yb, b['MAP'], dd, fb, fp) for n, dd, fb, fp in arms]
    print(f"===== {kind} =====")
    for state, idx in (('rest', 2), ('exercise + PVD', 3)):
        print(f"-- {state}")
        print(f"{'arm':30s} | RV Ees  RV Ea  RV Ees/Ea | LV Ees/Ea | RVSV  PAs", flush=True)
        for row in built:
            r, _ = simulate(row[idx], row[1], y0=yb)
            print(f"{row[0]:30s} | {r['RV_Ees']:6.2f} {r['RV_Ea']:6.2f}  {r['RV_coupling']:8.2f} | "
                  f"{r['LV_coupling']:9.2f} | {r['RVSV']:4.0f} {r['PAs']:5.1f}", flush=True)
