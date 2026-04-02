# Phase 2: Knowledge Classification — DSSAT-CSM Pipeline

> For each pipeline stage, knowledge is classified into three types that map to
> infrastructure layers: **Procedural** → Validated Tools, **Evaluative** → Skill
> Documents, **Debugging** → Diagnostic Triplets.

---

## S1: Experiment Design

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P1.1 | FileX fixed-column FORMAT rules (I3, A8, etc.) | ipexp.for:1000-1064 |
| P1.2 | YYDDD ↔ YYYYDDD date conversion (Y2K logic) | ipexp.for:184-191 |
| P1.3 | Experiment code naming convention (8-char: SSSSYYYY) | ipexp.for:288 |
| P1.4 | Section marker syntax (*EXP.D, *TREAT, *CULTI, etc.) | ipexp.for |
| P1.5 | Treatment factor cross-reference validation | ipexp.for:55 |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E1.1 | Choosing treatment structure (factorial vs single) |
| E1.2 | Mapping real-world experiment to DSSAT factor levels (CU, FL, SA, IC, MP, MI, MF, MR, MC, MT, ME, MH, SM) |
| E1.3 | Deciding which sections are needed vs optional |
| E1.4 | Cross-referencing WSTA code with available weather files |
| E1.5 | Cross-referencing ID_SOIL with available soil profiles |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D1.1 | "Treatment input section not found" (Error 1) | fatal |
| D1.2 | "Error in Experiment Selection entry" (Error 2) | fatal |
| D1.3 | "File not found" (Error 29) — path construction bug | fatal |
| D1.4 | SLNO='-99' silently applies default soil (no warning) | silent |
| D1.5 | "File only for spatial analysis" (Error 99) | fatal |

---

## S2: Weather Preparation

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P2.1 | .WTH fixed-format: @DATE SRAD TMAX TMIN RAIN (YYDDD) | IPWTH_alt.for |
| P2.2 | TAV calculation: mean annual temperature from daily data | weathr.for:306 |
| P2.3 | TAMP calculation: half-range of monthly mean temperatures | weathr.for:306 |
| P2.4 | Station header format: @INSI LAT LONG ELEV TAV AMP REFHT WNDHT | IPWTH_alt.for |
| P2.5 | NaN → -99 conversion for all weather variables | IPWTH_alt.for:1027-1039 |
| P2.6 | Unit expectations: SRAD=MJ/m²/d, T=°C, RAIN=mm/d, WIND=km/d | weathr.for |
| P2.7 | Weather file naming: [SSSS]YYMM.WTH | MAKEFILEW.f90 |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E2.1 | Choosing measured vs generated weather (MEWTH=M vs G) |
| E2.2 | Deciding whether to gap-fill missing days or use weather generator |
| E2.3 | Verifying station coordinates match field location |
| E2.4 | Judging whether SRAD < 1.0 is instrument error vs real overcast |
| E2.5 | Assessing whether REFHT/WNDHT matter for the chosen ET method |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D2.1 | "Solar radiation data error" (ErrCode 2): SRAD <0 or >100 | fatal |
| D2.2 | "Tmax is less than Tmin" (ErrCode 6) | fatal |
| D2.3 | "Non-sequential data in file" (ErrCode 8) | fatal |
| D2.4 | SRAD < 0.1 silently reset to 0.1 (WARNING only) | silent |
| D2.5 | NaN in weather silently converted to -99 | silent |
| D2.6 | TMAX ≈ TMIN (diff < 0.05°C) — WARNING not ERROR | warning |
| D2.7 | TAV ≤ 0 silently defaulted to 20°C | silent |
| D2.8 | TAMP ≤ 0 silently defaulted to 5°C | silent |
| D2.9 | "Weather record not found" (ErrCode 10) — missing day | fatal |

---

## S3: Soil Setup

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P3.1 | .SOL fixed-format: PEDON, SLSOUR, SLTXS, SLDP, then layer data | IPSOIL_Inp.for:355-406 |
| P3.2 | Van Genuchten parameter estimation from texture class | RETC_VG.for:897-943 |
| P3.3 | Brooks & Corey lambda from LL/DUL/SAT | RETC_VG.for:992-1034 |
| P3.4 | Texture classification (12 classes → coarse/fine grouping) | RETC_VG.for:878-884 |
| P3.5 | Water limit ordering enforcement: LL < DUL < SAT | IPSOIL_Inp.for:496-538 |
| P3.6 | Residual water content (wcr) from texture-specific wcr_wcpwp ratios | RETC_VG.for:992-1023 |
| P3.7 | Automatic minimum gap enforcement: SAT = DUL + 0.01 if equal | IPSOIL_Inp.for:530 |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E3.1 | Choosing SLDR (drainage rate) and SLRO (runoff curve number) |
| E3.2 | Setting SLPF (soil fertility factor) — model calibration parameter |
| E3.3 | Deciding number of layers and depths (1-20) |
| E3.4 | Interpreting lab data into DSSAT format (unit conversions) |
| E3.5 | Choosing between measured vs estimated hydraulic properties |
| E3.6 | Selecting MESOL (layer redistribution method: 1, 2, or 3) |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D3.1 | "SAT < DUL" (Error 7) — water ordering violation | fatal |
| D3.2 | "LL > DUL" (Error 8) — water ordering violation | fatal |
| D3.3 | "Layer exceeds maximum (NL=20)" (Error 2) | fatal |
| D3.4 | "Soil profile missing from file" (Error 4) | fatal |
| D3.5 | SWCON < 0 silently reset to -99 | silent |
| D3.6 | SLNF > 1.0 silently clamped to 1.0 (WARNING if ISWNIT=Y) | silent |
| D3.7 | Shallow soil (<20cm) causes division-by-zero in SOC_40CM | silent |
| D3.8 | Layer capped at NL=20 without warning | silent |
| D3.9 | "SALB <= 0.0" (Error 12) — albedo invalid | fatal |

---

## S4: Genotype Configuration

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P4.1 | .CUL fixed-column format: VAR#(1-6), VRNAME(7-26), ECO#(32-37), coefficients | MZIXM048.CUL |
| P4.2 | Coefficient range validation (MINIMA/MAXIMA rows) | .CUL files line 40-41 |
| P4.3 | ECO# cross-reference to .ECO file | ipexp.for |
| P4.4 | Model-specific coefficient sets (CERES vs CROPGRO vs IXIM) | Plant/*/IPCROP |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E4.1 | Selecting an existing cultivar vs creating a new one |
| E4.2 | Calibrating P1/P2/P5 from phenological observations |
| E4.3 | Calibrating G2/G3 from yield component data |
| E4.4 | Understanding PHINT sensitivity to location |
| E4.5 | Choosing the right crop model for the cultivar (MZCER vs MZIXM) |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D4.1 | "Error in cultivar input" (Error 11) — INGENO not found in .CUL | fatal |
| D4.2 | "Crop not available in model" (Error 20) | fatal |
| D4.3 | Coefficient outside MINIMA/MAXIMA range — no error, wrong phenology | silent |
| D4.4 | Wrong crop model selected (e.g., MZCER vs MZIXM) — plausible but wrong output | silent |

---

## S5: Simulation Controls

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P5.1 | Switch value enumerations (MEEVP={R,Z}, MESOM={P,G}, etc.) | IPSIM.for |
| P5.2 | Default switch assignments | IPSIM.for:137-146 |
| P5.3 | Column positions for switch reading (MEEVP=col37, MESOM=col67, etc.) | IPSIM.for:1446-1472 |
| P5.4 | Output detail level encoding (IDETO/IDETS: Y/N/A/D) | IPSIM.for |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E5.1 | Choosing ET method (Ritchie vs Priestley-Taylor vs Penman-Monteith) |
| E5.2 | Choosing SOM method (Godwin vs Century) |
| E5.3 | When to enable/disable water, N, P, K simulation |
| E5.4 | Setting appropriate output detail levels |
| E5.5 | Interaction effects between switches (e.g., ISWNIT requires ISWWAT) |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D5.1 | Invalid switch value silently replaced by default | silent |
| D5.2 | ISWNIT='Y' but ISWWAT='N' — inconsistent (N needs water) | degraded |
| D5.3 | "Simulation must begin on or before planting date" (Error 4) | fatal |

---

## S6: Initial Conditions

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P6.1 | IC layer depth matching to soil profile layers | SEINIT.for |
| P6.2 | SH2O range enforcement: LL ≤ SH2O ≤ SAT | SEINIT.for |
| P6.3 | Default NO3/NH4 initialization when missing | SEINIT.for |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E6.1 | Setting initial soil water (field capacity vs wilting point vs measured) |
| E6.2 | Estimating initial NO3/NH4 profile when no measurements available |
| E6.3 | Deciding previous crop residue amount and C:N ratio |
| E6.4 | Spin-up strategy (multi-year warm-up vs single year) |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D6.1 | IC layer depths don't match soil profile — interpolation artifacts | degraded |
| D6.2 | SH2O > SAT silently clamped — overestimation masked | silent |
| D6.3 | Very high initial NO3 causes unrealistic early growth | silent |

---

## S7: Management Specification

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P7.1 | Irrigation method code lookup (IROP 001-011) | SEIRR.for:48-59 |
| P7.2 | Fertilizer method code validation (FMCD 001-998) | IPMAN.for:134 |
| P7.3 | Tillage implement code validation (TLIMP 001-998) | IPTILL.for:78-82 |
| P7.4 | Management record FORMAT (I3,I5,1X,A5,1X,F5.0,...) | IPMAN.for:60 |
| P7.5 | Date sequencing validation (operation dates within simulation period) | IPFERT.for, IPIRR.for |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E7.1 | Setting planting density and depth for the target crop |
| E7.2 | Designing irrigation schedule (amount, timing, method) |
| E7.3 | Designing fertilizer split application strategy |
| E7.4 | Choosing automatic vs prescribed management |
| E7.5 | Setting harvest criteria (maturity-based vs date-based) |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D7.1 | "First fertilizer date prior to start" (IPFERT Error 3) | warning |
| D7.2 | "Harvest date prior to start" (IPHAR Error 6) | fatal |
| D7.3 | Operations exceed NAPPL=9000 limit | fatal |
| D7.4 | Harvest after plant death silently skipped | silent |
| D7.5 | Wrong FMCD code applies fertilizer to wrong depth/method | silent |

---

## S8: Batch Execution

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P8.1 | Batch file format: $BATCH header, experiment/treatment records | CSM.for:238-242 |
| P8.2 | CMake build procedure for dscsm048 | CMakeLists.txt |
| P8.3 | DYNAMIC state machine sequence (1→2→3→4→5→6→7) | LAND.for |
| P8.4 | Run mode codes (A/B/C/D/E/F/G/I/L/N/Q/S/T/Y) | CSM.for:195 |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E8.1 | Choosing run mode (single vs batch vs sensitivity) |
| E8.2 | Interpreting MODEL.ERR messages during runtime |
| E8.3 | Diagnosing why simulation stops early |
| E8.4 | Understanding the DYNAMIC state machine flow |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D8.1 | Fortran runtime SIGFPE — division by zero in RATE calculations | fatal |
| D8.2 | High altitude thermal time collapse (TT→0) | fatal |
| D8.3 | Compilation failure — missing Fortran compiler or CMake | fatal |
| D8.4 | "Output.CDE not found" (Error 30) | fatal |
| D8.5 | Simulation hangs — infinite loop in auto-planting | fatal |
| D8.6 | Zero-divide in SOC_40CM for shallow soils | fatal |

---

## S9: Output Parsing

### Procedural Knowledge (→ Tools)
| ID | Knowledge Item | Source |
|----|----------------|--------|
| P9.1 | Summary.OUT column layout and variable types | OPSUM.for:39-90 |
| P9.2 | Missing value convention (-99, -99.0) | OPSUM.for |
| P9.3 | YYDDD → calendar date conversion for ADAT/MDAT/PDAT | OPSUM.for |
| P9.4 | PlantGro.OUT daily format and column headers | OPGROW.for |
| P9.5 | Evaluate.OUT measured vs simulated column pairing | OPSUM.for |

### Evaluative Knowledge (→ Skill Document)
| ID | Knowledge Item |
|----|----------------|
| E9.1 | Judging whether yield (HWAH) is reasonable for the crop/region |
| E9.2 | Interpreting phenological date output (ADAT, MDAT) |
| E9.3 | Diagnosing poor simulation from output patterns |
| E9.4 | Comparing simulated vs observed: what metrics to use (RMSE, d-index, EF) |

### Debugging Knowledge (→ Triplets)
| ID | Symptom | Severity |
|----|---------|----------|
| D9.1 | All -99 in Summary.OUT — simulation didn't produce results | fatal |
| D9.2 | HWAH = 0 but simulation completed — crop never reached maturity | degraded |
| D9.3 | ADAT > MDAT — phenological dates reversed (date format error) | silent |
| D9.4 | Incomplete output files — crash during RATE with no file close | degraded |

---

## Summary Counts

| Stage | Procedural Items | Evaluative Items | Debugging Items |
|-------|:---:|:---:|:---:|
| S1 Experiment Design | 5 | 5 | 5 |
| S2 Weather Prep | 7 | 5 | 9 |
| S3 Soil Setup | 7 | 6 | 9 |
| S4 Genotype Config | 4 | 5 | 4 |
| S5 Simulation Controls | 4 | 5 | 3 |
| S6 Initial Conditions | 3 | 4 | 3 |
| S7 Management Spec | 5 | 5 | 5 |
| S8 Batch Execution | 4 | 4 | 6 |
| S9 Output Parsing | 5 | 4 | 4 |
| **TOTAL** | **44** | **43** | **48** |

**High-priority dissection targets** (practitioner said "you just learn with experience"):
- D2.5: NaN silently masked as -99 in weather
- D3.7: Shallow soil causes zero-divide with no error message
- D4.4: Wrong crop model gives plausible but wrong output
- D5.2: Switch interactions (ISWNIT needs ISWWAT)
- D8.2: High-altitude thermal time collapse
- D9.3: Phenological dates can be silently reversed

---

*Classification based on DSSAT v4.8.5 codebase analysis. Practitioner review pending.*
