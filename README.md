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

## Desktop interface

```
python launcher.py             # needs matplotlib for the plots: pip install matplotlib
```

**Scenario builder** tab: tune one patient and compare a treated scenario against the
same patient untreated (table of pressures, volumes, flows and coupling; LV, RV and atrial
PV loops; LA/RA/PA pressure waveforms). Controls:

- Patient: HFpEF or HFrEF twin, sinus rhythm or AF, rest or exercise (optionally with
  pulmonary vascular disease), and multipliers on contractility, diastolic stiffness,
  SVR, PVR, PA compliance, venous capacitance and stressed volume; pericardium and septal
  interaction.
- Interatrial shunt 0-10 mm, discharge coefficient, acute or chronic (reflex volume
  retention and post-shunt PVR rise, with editable gain and PVR rise).
- Mitral and tricuspid regurgitation: none/mild/moderate/severe, modeled as a fixed
  effective regurgitant orifice area (MR 0.10/0.30/0.50 cm^2, TR 0.10/0.30/0.70 cm^2,
  editable), optionally with chronic volume compensation. The resulting regurgitant
  volume and fraction are reported with their guideline class.
- Therapies: baroreflex activation (0-100%), sotatercept (0-100%, a PVR reduction of up
  to 30%), pulmonary artery denervation (yes/no). Effect sizes are assumptions and are
  editable in the panel.

The same engine is available from Python as `scenario.run_scenario` (see `scenario.py`).
A run takes about 40-90 s; the untreated patient is cached when only therapies change.

**Paper scripts** tab: runs the `run_*.py` scripts below and shows their output.

### Sharing the app (Windows)

```
python make_release.py         # writes dist/CardioSight-Shunt-Simulator-<date>-<commit>.zip
```

The recipient extracts the zip and double-clicks `install.bat` (instructions in
`INSTALL.txt`). The installer needs no administrator rights. It copies the app to
`%LOCALAPPDATA%\Programs\CardioSight Shunt Simulator` and finds Python 3.8+, installing it
with winget if it is missing. It then creates a private `.venv` with matplotlib, runs
`test_baseline.py`, and adds Desktop and Start Menu shortcuts. `uninstall.bat` in the
install folder removes everything.

## What each script reproduces

| Script | Paper section | Run time |
| --- | --- | --- |
| `run_acute.py` | Methods baseline table; Results 1, acute effects at rest | ~15 s |
| `run_rv_compliance.py` | Results 1, right-heart compliance in isolation | a few minutes |
| `run_scenarios.py` | Results 2, exercise, pulmonary vascular disease, volume retention | a few minutes |
| `run_reflex.py` | Results 3, cardiac arm against volume arm (gain sweep) | a few minutes |
| `run_echo_matrix.py` | Results 3, settings that match the trial echocardiograms; operating stiffness | a few minutes |
| `run_bat.py` | Results 4, predicted effect of adding baroreflex activation therapy (assumed effect sizes) | about 7 minutes |
| `run_la_volume.py` | Results 3, left atrial volume: extra retention and ventricular interaction (run once per twin: `HFpEF`, `HFrEF`) | about 5 minutes |
| `run_af.py` | Results 3, loss of atrial contraction and left atrial volume (run once per twin) | about 3 minutes |
| `run_padn.py` | Extension: shunt with pulmonary artery denervation (PADN), assumed effect sizes (run once per twin) | about 3 minutes |
| `run_triple.py` | Extension: shunt with BAT and PADN together (run once per twin) | about 4 minutes |
| `run_coupling.py` | Extension: RV and LV ventriculo-arterial coupling (Ees/Ea) for the triple-therapy arms (run once per twin) | about 4 minutes |

`expected_output/` holds the printed output of each script for a 6 mm shunt, so
you can compare your run with the numbers in the paper.

## The model

`model.py` contains everything: parameters for both twins, the equations, the
integrator and the scenario helpers.

- **Chambers.** LV, RV, LA and RA use time-varying elastance:
  `P = e(t)*Ees*(V-V0) + (1-e(t))*A*(exp(B*(V-V0))-1)`.
- **Vessels.** Systemic arteries, systemic veins, pulmonary arteries and a
  pulmonary venous reservoir are linear capacitances joined by resistances.
  Valves pass forward flow only, unless MR/TR is set (regurgitant orifice, `scenario.py`).
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

- Two hand-tuned twins. The HFrEF twin matches the RELIEVE-HF baseline medians
  for LVEF (about 29%) and LV end-diastolic volume only.
- The shunt is a 6 mm sharp-edged orifice with `Cd` = 0.7 (effective area
  19.8 mm^2). That equals a 5.1 mm lumen with `Cd` = 0.97, i.e. a Venturi-like
  device. Calibrate `Cd` against bench or clinical data for a specific device.
  Set the `SHUNT_CD` environment variable to change it for any script, e.g.
  `SHUNT_CD=0.8 python run_triple.py HFpEF` (output in
  `expected_output/run_triple_cd08.txt`).
- `run_padn.py` and `run_triple.py` are not yet described in the paper. Their
  BAT and PADN effect sizes are assumptions, so treat the output as predictions.
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
