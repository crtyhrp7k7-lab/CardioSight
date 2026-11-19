# Chamber elastance and EDPVR parameters: literature review and fitting bounds

Scope: Ees and the diastolic pressure–volume (EDPVR) parameters for LV, RV, LA and RA in
healthy adult males, HFpEF males and HFrEF males, mapped onto this repository's chamber model.

Revision 2, 2026-11-19. Full texts of Westermann 2008 (with the Kass letter and authors' reply),
Zile 2004, Rain 2013, Rommel 2018 and ten Brinke 2010 have now been read. Revision 1
(2026-11-17) was abstract-only. **Several conclusions changed**; see §0.

Research model only; not for clinical use.

---

## 0. What changed from revision 1

| Item | Rev 1 | Rev 2 | Why |
|---|---|---|---|
| LV B, healthy | 0.020–0.050 (Klotz-inferred) | **0.006–0.020** | Measured exponential fits: Westermann median 0.0098 /mL, Zile 0.01 ± 0.01 /mL. The Klotz power-law conversion overestimated B by about 3–4× (§4.2) and is no longer used for bounds |
| LV B, HFpEF | 0.030–0.080 | **0.012–0.050** | Westermann median 0.028 (IQR 0.022–0.038), Zile corrected 0.03 ± 0.01 |
| LV B, HFrEF | 0.010–0.035 | **0.004–0.020** | Still no direct exponential data. Scaled down from the healthy value because HFrEF chambers are dilated |
| LV Ees, healthy | 1.0–3.5 | **0.7–3.5** | Conductance-catheter controls run lower than the Kass group: Westermann 0.95, ten Brinke 1.30, Rommel 2.89 |
| LV Ees, HFrEF | 0.3–1.5 (inferred) | **0.3–2.0** (measured) | ten Brinke VCO: 1.11 ± 0.63 mmHg/mL, n=19, EF about 27% |
| RV β source | Rain 2013 as healthy anchor | **Rain excluded from male bounds** | All 7 Rain controls were **female**, and β was fitted on a **normalized** volume axis |
| RV B, all groups | 0.010–0.060 | **0.003–0.025** | Rommel 2018 conductance + caval occlusion. Its β appears to be per BSA-indexed volume (§4.5) |
| RV Ees, HFpEF | values ✖ | **0.69 ± 0.27** vs control **0.49 ± 0.16** | Rommel 2018 |
| Notation | "no reversal found" | **Notation clash found** (§5) | Westermann's "b" is a linear slope in mmHg/mL; Zile's "b" is the exponent in 1/mL |

---

## 1. Target formulation (this model)

`model.py` uses, for every chamber:

```
P(V,t) = e(t)·Ees·(V − V0) + (1 − e(t))·A·(exp(B·(V − V0)) − 1)
```

| Symbol | Role | Units |
|---|---|---|
| Ees | end-systolic elastance (slope of a linear ESPVR) | mmHg/mL |
| V0  | shared unstressed volume (ESPVR intercept **and** EDPVR zero-pressure volume) | mL |
| A   | EDPVR scale ("α" below) | mmHg |
| B   | EDPVR exponent / chamber stiffness constant ("β" below) | 1/mL, **absolute** (not BSA-indexed) volume |

Local end-diastolic chamber stiffness: `dP/dV = B·(P + A)`. Equivalently, `d ln(P + A)/dV = B`.

## 2. Evidence grading

| Tag | Meaning |
|---|---|
| **M** | Directly measured in humans (invasive P–V loops with preload reduction / multi-beat ESPVR or EDPVR) |
| **M3** | Measured invasively, but the EDPVR is fitted to only about 3 points within one beat (Zile) |
| **SB** | Single-beat estimate (assumes a normalized elastance curve or EDPVR shape: model-based) |
| **E** | Echo/imaging-derived surrogate (e.g. a chord slope ΔP/ΔV, not a fitted exponential) |
| **An** | Animal data, used only as plausibility context, never as a bound anchor |
| **I** | Inferred here by conversion or scaling (assumptions stated) |
| ✔F | Value read from the **full text** in this revision |
| ✔a | Value read from the abstract only |

**Sex.** No source reports male-only values. The male share of each cohort is listed in every
row. Men dominate only in Zile DHF (31/47), ten Brinke (CABG 10/12, HF 12/19) and Rommel
controls (6/9). Rain was all-female and is excluded from male bounds.

## 3. Evidence tables

### 3.1 LV — Ees

| Population (n, % male, age) | Ees, mmHg/mL | ESPVR definition | Method | Grade | Citation |
|---|---|---|---|---|---|
| Chest-pain controls without HF (20, 45% M, 55 y) | **0.95** median (IQR 0.8–1.1) | Linear ESPVR, IVC occlusion | Conductance catheter, cath lab, awake | M ✔F | Westermann D et al. *Circulation* 2008;117:2051–2060 (Table 4) |
| HFNEF (70, 43% M, 58 y, EF 65%) | **1.1** (0.95–1.25), p = 0.24 vs control | same | same | M ✔F | same |
| CABG patients with normal LV function (12, 83% M, 59 y) | VCO **1.30 ± 0.91**; SB 1.12 ± 0.66 | Linear ESPVR, vena cava occlusion; SB = Takeuchi-type | Conductance, **intra-operative, anaesthetised** | M ✔F | ten Brinke EA et al. *Acta Physiol* 2010;198:37–46 (Tables 2–3) |
| HFrEF, NYHA III–IV, RMA ± SVR (19, 63% M, EF 25–29%, EDV 201–228 mL) | VCO **1.11 ± 0.63**; SB 0.73 ± 0.48 | same | same | M ✔F | same |
|   RMA subgroup (9, 44% M, EF 29%) | VCO 0.88 ± 0.47 | same | same | M ✔F | same |
|   SVR subgroup (10, 80% M, EF 25%) | VCO 1.32 ± 0.71 | same | same | M ✔F | same |
| Controls without HF (9, 67% M, 60 y) | **2.89 ± 1.10** ("LV ESPVR") | Not stated separately for LV ("similarly…") | Conductance + CMR volume calibration | M ✔F | Rommel KP et al. *Circ Heart Fail* 2018;11:e004121 (Table 2) |
| HFpEF (24, **8% M**, 66 y) | **3.20 ± 1.16** | same | same | M ✔F | same |
| Normotensive controls | 2.1 ± 0.9 | Linear ESPVR | Conductance | M ✔a | Kawaguchi M et al. *Circulation* 2003;107:714–720 |
| HFpEF (10) | 4.7 ± 1.5 | same | same | M ✔a | same |
| Community controls / HFpEF (617 / 244, 45% M) | 1.99 ± 0.59 / 2.42 ± 0.90 | Single-beat (Chen 2001) | Echo + cuff | SB ✔F | Borlaug BA et al. *JACC* 2009;54:410–418 |

**Method spread.** Healthy LV Ees spans about 1 to 2.9 mmHg/mL across groups using the same
"gold standard". Conductance-catheter volume calibration (parallel conductance, α factor) is a
known source of between-lab offset. Kass's letter on Westermann 2008 (*Circulation*
2009;119:e4) explicitly raised "methodology problems (eg, catheter calibration)" in the
control group. The authors' reply (e5) defended the calibration. Treat between-lab differences
as **method variance**, not biology, and let the bounds span them.

### 3.2 LV — diastolic (EDPVR)

| Population | Equation (as published) | Scale (A) | Exponent (β) | Context | Method | Grade | Citation |
|---|---|---|---|---|---|---|---|
| Controls (20, 45% M) | "Exponential fitting" of the EDPVR during IVC occlusion; exact form not printed (cites Burkhoff 2005) | not reported | **0.0098** median (IQR 0.009–0.011), units implied 1/mL | EDP 5.6 mmHg, EDV 158 mL | Conductance + IVC occlusion | M ✔F | Westermann 2008 (Table 3) |
| HFNEF (70, 43% M) | same | not reported | **0.028** (0.022–0.038) | EDP 16.1, EDV 151 mL | same | M ✔F | same |
| Controls (10, sex not reported, 58 y, BSA 2.1) | **P = A·e^(bV)**, V absolute, 3 points per beat (Pmin, pre-A, EDP) | **2.3 ± 0.8 mmHg** | **0.01 ± 0.01 /mL** | EDP 8 ± 2, EDV 115 ± 9 mL | Micromanometer + echo/Doppler volumes | M3 ✔F | Zile MR et al. *NEJM* 2004;350:1953–1959 (Table 1) |
| DHF (47, **66% M**, 59 y, BSA 2.2), measured | same | 6.5 ± 4.3 | 0.02 ± 0.01 | EDP 25 ± 6, EDV 103 ± 22 | same | M3 ✔F | same |
| DHF, **corrected** | same, with Pmin corrected for incomplete relaxation (τ-based subtraction, Fig. 1) | 1.5 ± 1.1 | **0.03 ± 0.01** | same | same | M3 ✔F | same |
| Controls (9, 67% M) / HFpEF (24, 8% M) | Linear "LV EDPVR" slope | — | 0.09 ± 0.01 / 0.14 ± 0.04 **mmHg/mL** (slope, not an exponent) | LVEDP 13.0 / 18.9 | Conductance | M ✔F | Rommel 2018 (Table 2) |
| Controls / HFNEF | "Stiffness b" = dP/dV, linear | — | 0.09 (0.07–0.12) / 0.24 (0.16–0.37) **mmHg/mL** | — | Conductance | M ✔F | Westermann 2008 (Table 3) |
| 80 ex-vivo hearts + in vivo | **Power law** EDP = An·EDVn^Bn, An = 28.2, Bn = 2.79 | — | — | normalized volume | Ex vivo + SB | SB ✔a | Klotz S et al. *AJP Heart* 2006;291:H403 |
| HFrEF CRT candidates (22, EF 29%) | — | — | — | EDV 257 ± 67, EDP 18 ± 8 | Conductance | M ✔a | Steendijk P et al. *Circulation* 2006;113:1295 |

Notes:
- **Zile's ± values are rounded to one significant figure**, so b = 0.01 ± 0.01 hides a lot. Back-solving b from mean A and mean EDP/EDV gives 0.011 (control), 0.013 (DHF measured) and 0.027 (DHF corrected). The mean of fitted (A, b) pairs does not reproduce the mean EDP (DHF measured: 6.5·e^(0.02·103) = 51 mmHg vs a measured 25). **Never combine a published mean A with a published mean b**; A and b are strongly anti-correlated.
- Westermann reports medians and IQRs, not mean ± SD.
- **HFrEF LV exponential β: still no direct source.** ten Brinke and Steendijk give volumes and Ees but no EDPVR exponent.

### 3.3 RV

| Population | Parameter | Value | Equation / definition | Method | Grade | Citation |
|---|---|---|---|---|---|---|
| Controls (9, 67% M, 60 y, BSA 2.01) | RV Ees | **0.49 ± 0.16 mmHg/mL** (caval occlusion; n=9) | Linear ESPVR through end-systolic points during IVC balloon occlusion | Conductance, volume-calibrated to CMR | M ✔F | Rommel 2018 (Results text) |
| HFpEF (23 analysable, 8% M, 66 y, BSA 1.93) | RV Ees | **0.69 ± 0.27** (p = 0.04) | same | same | M ✔F | same |
| both | V0 (ESPVR intercept) | 8.8 ± 19.0 vs 16.3 ± 17.2 mL (group order not stated; p = 0.35) | — | — | M ✔F | same |
| Controls / HFpEF | "RV ESPVR" (Table 2, baseline) | 0.47 ± 0.08 / 0.83 ± 0.55 mmHg/mL | Not the same numbers as the caval-occlusion Ees above; method for the table value is unclear | — | M ✔F | same |
| Controls | RV β | **0.012 ± 0.003** | Printed as "EDP=C·?·EDV" (symbol glyphs lost in text extraction). Reads as **EDP = C·e^(β·EDV)** per the cited LV method. **Volumes indexed to BSA**: β is likely in 1/(mL/m²) (§4.5) | same | M ✔F | same |
| HFpEF | RV β | **0.018 ± 0.003** (p < 0.01) | same | same | M ✔F | same |
| Controls / HFpEF | linear RV EDPVR slope | 0.03 ± 0.01 / 0.06 ± 0.02 mmHg/mL | — | — | M ✔F | same |
| Controls / HFpEF | RV EDP, RV EDVi | 4.1 ± 1.3 / 7.2 ± 1.8 mmHg; 68.4 ± 10.9 / 66.4 ± 13.9 mL/m² | — | — | M ✔F | same |
| Controls (7, **0% M**, 54 y) | RV β | 0.029 ± 0.003 (Table 2 says **SD**, abstract says **SEM**) | **P = α(e^(βV) − 1)**, fitted through (0,0), (BDV, 1 mmHg) and (EDVn, EDPn). **EDV normalized to the cohort-maximal EDV**; BDP normalized to 1 mmHg | Single-beat; MRI volumes | SB ✔F | Rain S et al. *Circulation* 2013;128:2016–2025 |
| PAH (21, 5% M) | RV β, α | β 0.050 ± 0.005; α 0.003 ± 0.001 (control α 0.007 ± 0.002) | same | same | SB ✔F | same |
| Controls/PAH | RV Ees | definition only: **Ees = (Piso − mPAP)/SV** | Single-beat | — | SB ✔F | same |
| Normal RV (9) | Emax | 1.30 ± 0.84 mmHg/mL, **V0 = 46 ± 21 mL** | Isochronal | Hi-fi + biplane cine | M ✔a | Dell'Italia LJ, Walsh RA. *Cardiovasc Res* 1988;22:864 |
| PAH (controls 15) | Eed | 0.53–0.91 mmHg/mL (PAH) | SB tangent stiffness | — | SB ✔a | Trip P et al. *Eur Respir J* 2015;45:1603 |

**Rain 2013 is not usable as a physical male RV B.** Its volume axis is rescaled per subject, the
curve is forced through the origin, and every control was female. Its β ratio (PAH/control ≈ 1.7)
is the only transferable information.

**HFrEF RV:** still no verified human Ees or β with a stated equation. Bounds are **I**.

### 3.4 LA (unchanged from rev 1, abstract-level)

| Population | Parameter | Value | Definition | Method | Grade | Citation |
|---|---|---|---|---|---|---|
| Controls (20) | LA Ees; LA stiffness | 0.61 ± 0.07; 0.13 ± 0.04 mmHg/mL | Linear ESPVR; slope of the filling limb | Echo LA volume + PCWP, saline loading | E ✔a | Dernellis JM et al. *Am J Cardiol* 1998;81:1138 |
| Recent MI (20) | same | 0.80 ± 0.09; 0.22 ± 0.05 | same | same | E ✔a | same |
| CHF, reduced LV function (20) | same | **0.22 ± 0.05**; 0.27 ± 0.05 | same | same | E ✔a | same |
| HFpEF vs HFrEF (198; mean LAP 20 vs 20) | LA stiffness | 0.79 vs 0.48 mmHg/mL | Chord stiffness (definition ✖) | Cath + echo | E ✔a | Melenovsky V et al. *Circ Heart Fail* 2015;8:295 |
| Dogs | LA Emax / Ees | 5.5 ± 2.8 / 4.3 ± 1.5 | Isochronal linear | Sonomicrometry | An ✔a | Hoit BD et al. *Circulation* 1994;89:1829 |

### 3.5 RA

No human RA Ees or exponential EDPVR measurement was found. RA bounds are **I** and weakly
identifiable.

## 4. Formulation conversions

1. **`A·e^(bV)` (Zile, Rommel, likely Westermann) → model.** The exponent transfers directly
   (B = b), because `d ln(P + A_model)/dV = B` and `d ln P/dV = b` coincide wherever P ≫ A.
   The scale does not: `A_model ≈ A_pub·e^(b·V0)` only when the −1 term is negligible. **Never
   transfer A.** Recompute it from a measured (EDV, EDP): `A = EDP/(exp(B·(EDV − V0)) − 1)`.

2. **Klotz power law → model B: not used for bounds.** Matching the local log-slope at the
   end-diastolic point (`B = Bn·Pm/[(Vm − V0_Klotz)(Pm + A)]`) gave 0.032–0.049 /mL for healthy
   ventricles. Exponential fits over the whole diastolic range measure **0.010** (Westermann,
   Zile), so the local match overestimates by about 3–4×. A power law's log-slope rises steeply
   as V approaches V0_Klotz (about 0.54·EDV), so the "equivalent B" depends on where the match is
   made. This is exactly the cross-formulation pitfall the review set out to avoid: Klotz values
   are kept only as shape context.

3. **Chord/tangent stiffness → B (atria).** `B ≈ k/(P + A)`. Melenovsky at LAP 20 gives HFpEF
   LA ≈ 0.039 and HFrEF LA ≈ 0.023 /mL. These are central values, not bounds.

4. **Ees with a different V0.** `Ees = Pes/(Ves − V0)` at a fixed end-systolic point.
   Dell'Italia's RV Emax of 1.30 (V0 = 46 mL) re-anchors to about 0.4–0.6 mmHg/mL at V0 = 10–20
   mL. Rommel's RV V0 of 9–16 mL is already close to the model's 10–20 mL, so its Ees transfers
   with little adjustment.

5. **BSA-indexed β (Rommel RV).** Rommel states "Volumes were indexed to body surface area". A
   consistency check against its own linear RV EDPVR slope supports β being per mL/m²:

   | Group | β·EDP (if per mL) | β·EDP/BSA (if per mL/m²) | Reported linear slope |
   |---|---|---|---|
   | Control | 0.049 | **0.024** | 0.03 |
   | HFpEF | 0.130 | **0.067** | 0.06 |

   Converted to absolute volume (β/BSA): **control ≈ 0.0060 /mL, HFpEF ≈ 0.0093 /mL**. This is an
   inference (grade I). Confirm by reading the formula on the Methods page of the PDF, where the
   symbols did not survive text extraction. The bounds below cover both readings.

## 5. α/β notation: reversals and clashes

- **No true α↔β reversal** (scale and exponent swapped) was found in the five full texts.
  Westermann (β = exponent), Zile (A = scale, b = exponent), Rain (α = scale, β = exponent) and
  Rommel (C = scale, β = exponent) all use the scale-then-exponent order.
- **Notation clash, the practical hazard:** Westermann 2008 uses **"b" for linear chamber stiffness
  dP/dV (mmHg/mL)**, while Zile 2004 uses **"b" for the exponent (1/mL)**. Entering Westermann's
  b = 0.09 as an exponent would be a 9× error. Map every symbol by **units**, never by letter.
- **Same name, different volume axis:** "β" in Rain (normalized volume), Rommel (BSA-indexed volume,
  probably) and Westermann/Zile (absolute mL) are three different quantities.
- **Units test** (still the rule): an exponent is in 1/mL with magnitude about 0.003–0.1; a scale is
  in mmHg with magnitude about 0.01–10; a linear stiffness is in mmHg/mL with magnitude about
  0.02–1.

## 6. Proposed fitting bounds (model formulation, adult males, absolute volumes)

The bounds are conservative: they span between-lab method variance, plus about ±1.5–2 SD where
spread is reported. **A** should be computed from the target (EDV, EDP) pair (§4.1), with the A
range kept only as a sanity check.

| Chamber | Group | Ees (mmHg/mL) | B (1/mL) | A (mmHg) | Basis | Current twin (`model.py`) |
|---|---|---|---|---|---|---|
| **LV** | Healthy | **0.7 – 3.5** | **0.006 – 0.020** | 0.5 – 5 | Ees: Westermann M 0.95, ten Brinke M 1.30, Rommel M 2.89, Kawaguchi M 2.1. B: Westermann M 0.0098 (IQR 0.009–0.011), Zile M3 0.01 | — |
| | HFpEF | **0.8 – 6.5** | **0.012 – 0.050** | 0.1 – 8 | Ees: Westermann 1.1 → Kawaguchi 4.7 ± 1.5. B: Westermann 0.028 (0.022–0.038), Zile corrected 0.03 ± 0.01 | Ees 3.2 ✓, B 0.033 ✓ |
| | HFrEF | **0.3 – 2.0** | **0.004 – 0.020** (I) | 0.2 – 8 | Ees: ten Brinke VCO M 1.11 ± 0.63. B: healthy measured value scaled for dilatation (EDV 200–260 vs about 150 mL); no direct data | Ees 0.62 ✓, B 0.0125 ✓ |
| **RV** | Healthy | **0.25 – 1.0** | **0.003 – 0.018** | 0.2 – 5 | Ees: Rommel M 0.49 ± 0.16, Dell'Italia re-anchored. B: Rommel 0.006 (indexed reading) to 0.012 (per-mL reading) | — |
| | HFpEF | **0.3 – 1.4** | **0.005 – 0.025** | 0.2 – 5 | Rommel M: Ees 0.69 ± 0.27; β 0.0093 (indexed) to 0.018 (per mL) | Ees 0.60 ✓, B 0.022 ⚠ upper end |
| | HFrEF | **0.15 – 1.0** | **0.003 – 0.020** (I) | 0.2 – 5 | I only (dilated RV → lower B) | Ees 0.35 ✓, B 0.016 ⚠ upper end |
| **LA** | Healthy | **0.3 – 1.0** | **0.010 – 0.060** | 0.05 – 2 | Dernellis E, Melenovsky-I | — |
| | HFpEF | **0.2 – 1.0** | **0.025 – 0.080** | 0.05 – 2 | Melenovsky-I (≈ 0.039) | Ees 0.30 ✓, B 0.042 ✓ |
| | HFrEF | **0.1 – 0.6** | **0.012 – 0.045** | 0.05 – 2 | Dernellis CHF E (0.22 ± 0.05); Melenovsky-I (≈ 0.023) | Ees 0.22 ✓, B 0.030 ✓ |
| **RA** | All | **0.1 – 0.8** | **0.010 – 0.060** | 0.05 – 2 | I only, no human data | Ees 0.30–0.35 ✓, B 0.035–0.036 ✓ |

**Flags for the current twins.**
- **RV B is at or above the upper evidence range in both twins** (HFpEF 0.022, HFrEF 0.016). If the
  BSA-indexed reading of Rommel is confirmed, the measured absolute RV B is about 0.006 (control)
  and 0.009 (HFpEF) /mL, so the twins' RVs would be about 2× stiffer than measured. This matters
  for the RV compliance and shunt-loading results (`run_rv_compliance.py`).
- **LV Ees spread is mostly methodological.** Fit Ees jointly with V0, and quote fitted Ees relative
  to the method family the target data come from (conductance vs single-beat echo).
- HFrEF LV B (0.0125) now sits mid-range rather than below range: rev 1's Klotz-based bound was too
  high.

**Identifiability notes for the fitter.**
- Ees and V0 are strongly correlated. Bound V0 (0–40 mL for the ventricles, 0–20 mL for the atria)
  and re-anchor literature Ees to that V0 (§4.4).
- A and B trade off along the EDPVR. Constrain with at least two diastolic points, or eliminate A
  via the EDV/EDP identity.
- Atrial and RA parameters are weakly identifiable from cuff/echo data alone. Prefer priors
  centred on the evidence over uniform bounds.

## 7. Remaining gaps

1. **Confirm the Rommel β formula and units** (Methods page, PDF p. 3–4). This decides whether RV
   B is about 0.006–0.009 or about 0.012–0.018 /mL.
2. **HFrEF exponential EDPVR** (LV and RV): still no direct source. Candidates: conductance studies
   with IVC occlusion in DCM/CRT cohorts that report an EDPVR exponent.
3. **Male-specific values:** none. A sex-stratified analysis of any conductance cohort would close
   this gap.
4. **Atrial data** remain abstract-level (Dernellis 1998, Melenovsky 2015). Melenovsky's full text
   would give the LA stiffness definition and the control value.
5. Model-derived parameter sets (Smith 2004, Ursino 1998, Santamore & Burkhoff 1991,
   Burkhoff & Tyberg 1993) remain unverified and unused.

## References (full text read, rev 2)

- Westermann D, Kasner M, Steendijk P, et al. Role of left ventricular stiffness in heart failure with normal ejection fraction. *Circulation* 2008;117:2051–2060. doi:10.1161/CIRCULATIONAHA.107.716886
- Kass DA. Letter regarding Westermann et al. *Circulation* 2009;119:e4. doi:10.1161/CIRCULATIONAHA.108.788729
- Westermann D, et al. Response to letter. *Circulation* 2009;119:e5. doi:10.1161/CIRCULATIONAHA.108.803429
- Zile MR, Baicu CF, Gaasch WH. Diastolic heart failure — abnormalities in active relaxation and passive stiffness of the left ventricle. *N Engl J Med* 2004;350:1953–1959. doi:10.1056/NEJMoa032566
- Rain S, Handoko ML, Trip P, et al. Right ventricular diastolic impairment in patients with pulmonary arterial hypertension. *Circulation* 2013;128:2016–2025. doi:10.1161/CIRCULATIONAHA.113.001873
- Rommel KP, et al. (senior author Lurz P). Load-independent systolic and diastolic right ventricular function in HFpEF as assessed by resting and handgrip exercise pressure-volume loops. *Circ Heart Fail* 2018;11:e004121. doi:10.1161/CIRCHEARTFAILURE.117.004121
- ten Brinke EA, Klautz RJ, Verwey HF, et al. Single-beat estimation of the left ventricular end-systolic pressure-volume relationship in patients with heart failure. *Acta Physiol* 2010;198:37–46. doi:10.1111/j.1748-1716.2009.02040.x

Abstract-level sources: see the PMIDs in §3 (Kawaguchi 12578874, Borlaug 19628115 [full text in
PMC], Chen 11738311, Asanoi 2752553, Klotz 16428349, Steendijk 16520415, Dell'Italia 3256426,
Trip 25882798, Kuehne 15451801, Dernellis 9605056, Melenovsky 25593126, Hoit 8149549).
