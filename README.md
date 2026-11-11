# Interatrial shunt digital twins: HFrEF and HFpEF

A closed-loop, lumped-parameter cardiovascular model used to study why an
interatrial shunt might help in heart failure with reduced ejection fraction
(HFrEF) and harm in heart failure with preserved ejection fraction (HFpEF).

It accompanies the technical paper *Mechanistic Basis for Differential Effects
of Interatrial Shunting in HFrEF and HFpEF: A Lumped-Parameter Digital Twin
Analysis* (Alan Eskuri and Claude, 2026), which sets the model against the
RELIEVE-HF echocardiographic findings of
[Zile et al., JACC Cardiovasc Imaging 2026;19:1-15](https://doi.org/10.1016/j.jcmg.2025.08.005).

> **Research model only.** The two twins are hand-tuned representative patients,
> not fits to patient data. Nothing here has been validated against invasive
> measurements in shunt recipients. Not for clinical use.

## Quick start

Requires Python 3.8 or later. No third-party packages.

```
python test_baseline.py        # about 15 s; confirms your copy reproduces the baseline
python run_acute.py            # baseline vs 6 mm shunt, both twins
python run_acute.py 8          # same, 8 mm shunt
```

Every `run_*.py` script takes the shunt diameter in mm as an optional argument
(default 6), prints a table, and writes JSON to `results/`.

## What each script reproduces

| Script | Paper section | Run time |
| --- | --- | --- |
| `run_acute.py` | Methods baseline table; Results 1, acute effects at rest | ~15 s |
| `run_rv_compliance.py` | Results 1, right-heart compliance in isolation | a few minutes |
| `run_scenarios.py` | Results 2, exercise, pulmonary vascular disease, volume retention | a few minutes |
| `run_reflex.py` | Results 3, cardiac arm against volume arm (gain sweep) | a few minutes |
| `run_echo_matrix.py` | Results 3, settings that match the trial echocardiograms; operating stiffness | a few minutes |

`expected_output/` holds the printed output of each script for a 6 mm shunt, so
you can compare your run with the numbers in the paper.

## The model

`model.py` contains everything: parameters for both twins, the equations, the
integrator and the scenario helpers.

- **Chambers.** LV, RV, LA and RA use time-varying elastance:
  `P = e(t)*Ees*(V-V0) + (1-e(t))*A*(exp(B*(V-V0))-1)`.
- **Vessels.** Systemic arteries, systemic veins, pulmonary arteries and a
  pulmonary venous reservoir are linear capacitances joined by resistances.
  Valves pass forward flow only.
- **Shunt.** Sharp-edged orifice, `Q = Cd*A*sqrt(2*|dP|/rho)`, `Cd = 0.7`,
  driven by the instantaneous LA-RA pressure difference.
- **Pericardium (optional).** Exponential pressure that engages when total
  heart volume exceeds the twin's own no-shunt resting maximum.
- **Exercise.** Higher heart rate, lower systemic resistance, modest inotropy,
  recruited stressed volume; PVR falls 15%, or rises 40% with PA compliance down
  40% in the pulmonary vascular disease variant.
- **Volume arm of the reflex.** Added stressed volume
  `dV = gain*(MAP_set - MAP)`; infinite gain restores pre-shunt arterial pressure.
- **Numerics.** Fourth-order Runge-Kutta, 0.5 ms step, run in 40-beat blocks
  until mean LA pressure changes by less than 0.02 mmHg between blocks.

Units: mmHg, mL, s. Resistances are in mmHg*s/mL (multiply by 16.67 for Wood units).

### Using it for your own patient

```python
import copy
from model import HFPEF, simulate

p = copy.deepcopy(HFPEF)
p['PVR'] *= 1.5                      # for example, raise pulmonary vascular resistance
base, state = simulate(p)            # no shunt
shunt, _ = simulate(p, 8.0, y0=state)  # 8 mm shunt, warm-started
print(base['PCWP'], shunt['PCWP'], shunt['QpQs'])
```

`simulate` returns a dictionary of final-beat metrics (pressures, volumes, flows,
ejection fractions) and the final state.

## Known limitations

- Two hand-tuned twins. The HFrEF twin is more dilated and has a lower LVEF
  than typical trial populations.
- The ideal-orifice shunt probably overestimates flow for a real device of the
  same nominal diameter. Calibrate `Cd` against bench or clinical data.
- Reflex gains, the pulmonary vascular disease severity and arterial pressure
  as the sensed variable are assumptions.
- Chamber properties are fixed: no remodeling. No septal interaction beyond a
  shared pericardial pressure. No baroreflex dynamics; only steady states.
- The right-heart compliance sweep cannot fully match the starting wedge
  pressure at the stiffest setting (the volume search reaches its bound).

## Authorship

Alan Eskuri posed the research question, specified the study and proposed the
neurohormonal hypothesis the scripts test. Claude (Anthropic) designed and coded
the model and ran the simulations under his direction. The code has not yet been
independently reviewed.

## License

MIT. See `LICENSE`. To cite, see `CITATION.cff`.
