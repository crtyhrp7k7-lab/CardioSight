"""Baseline and acute shunt hemodynamics at rest for both twins.

Usage: python run_acute.py [shunt_diameter_mm]     (default 6)
Reproduces the Methods baseline table and the "Acute effects at rest" table.
"""
import json
import sys
from pathlib import Path
from model import TWINS, simulate

LABELS = [
    ('HR', 'Heart rate (bpm)'), ('CO', 'Systemic output, Qs (L/min)'),
    ('Qp', 'Pulmonary flow, Qp (L/min)'), ('QpQs', 'Qp:Qs'),
    ('Qsh', 'Shunt flow L->R (L/min)'), ('LA_RA', 'Mean LA-RA gradient (mmHg)'),
    ('PCWP', 'Mean LA pressure / PCWP (mmHg)'), ('LAv', 'LA v-wave peak (mmHg)'),
    ('LVEDP', 'LVEDP (mmHg)'), ('RAP', 'Mean RA pressure (mmHg)'),
    ('PAs', 'PA systolic (mmHg)'), ('PAd', 'PA diastolic (mmHg)'), ('mPAP', 'Mean PA pressure (mmHg)'),
    ('Ppv', 'Pulm. venous reservoir pressure (mmHg)'), ('PBV', 'Pulm. stressed volume (mL)'),
    ('AoS', 'Aortic systolic (mmHg)'), ('AoD', 'Aortic diastolic (mmHg)'), ('MAP', 'Mean arterial pressure (mmHg)'),
    ('LVEDV', 'LVEDV (mL)'), ('LVESV', 'LVESV (mL)'), ('LVSV', 'LV stroke volume (mL)'), ('LVEF', 'LVEF (%)'),
    ('RVEDV', 'RVEDV (mL)'), ('RVSV', 'RV stroke volume (mL)'), ('RVEF', 'RVEF (%)'),
    ('LAmax', 'LA max volume (mL)'), ('RAmax', 'RA max volume (mL)'),
]

if __name__ == '__main__':
    d_mm = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    out = {}
    for kind, p in TWINS.items():
        base, y = simulate(p)
        post, _ = simulate(p, d_mm, y0=y)
        out[kind] = dict(base=base, shunt=post)
        print(f"\n=== {kind}: no shunt vs {d_mm:g} mm shunt (acute, rest) ===")
        print(f"{'':40s}{'base':>9s}{'shunt':>9s}{'change':>9s}")
        for key, label in LABELS:
            print(f"{label:40s}{base[key]:9.2f}{post[key]:9.2f}{post[key] - base[key]:+9.2f}")
    res = Path(__file__).parent / 'results'
    res.mkdir(exist_ok=True)
    (res / 'acute.json').write_text(json.dumps(out, indent=1))
