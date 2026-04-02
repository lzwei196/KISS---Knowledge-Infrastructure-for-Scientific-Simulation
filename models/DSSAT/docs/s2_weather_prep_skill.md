# S2: Weather Preparation Skill

## Purpose

Prepare, format, and validate a DSSAT weather file (.WTH) from raw meteorological data so that it conforms to DSSAT v4.8.5 input requirements for daily weather-driven crop simulation. This document specifies every formatting rule, unit conversion, and quality check needed to produce a valid .WTH file.

## Prerequisites

- [ ] Raw daily weather data is available (from station records, reanalysis, or gridded products).
- [ ] The data contains at minimum: date, solar radiation, maximum temperature, minimum temperature, and rainfall.
- [ ] A 4-character weather station code (INSI) has been assigned or is known.
- [ ] Station latitude, longitude, and elevation are known.
- [ ] The user understands the YYDDD date format.

## Inputs

| Parameter | Type | Units | Description | Example |
|-----------|------|-------|-------------|---------|
| Station code | 4-char string | -- | Unique station identifier | `UFGA` |
| Latitude | Float | Decimal degrees (N+, S-) | Station latitude | `29.630` |
| Longitude | Float | Decimal degrees (E+, W-) | Station longitude | `-82.370` |
| Elevation | Float | Meters above sea level | Station elevation | `10` |
| Daily SRAD | Float | MJ/m2/day | Solar radiation | `5.9` |
| Daily TMAX | Float | Degrees Celsius | Maximum daily temperature | `24.4` |
| Daily TMIN | Float | Degrees Celsius | Minimum daily temperature | `15.6` |
| Daily RAIN | Float | mm/day | Total daily rainfall | `19.0` |
| Daily WIND | Float | km/day (optional) | Wind speed | `86.4` |
| Daily DEWP | Float | Degrees Celsius (optional) | Dewpoint temperature | `18.0` |
| Daily PAR | Float | moles/m2/day (optional) | Photosynthetically active radiation | `12.4` |
| Daily RHUM | Float | Percent (optional) | Relative humidity | `75.0` |

## Procedure

### Step 1: Assign the File Name

The .WTH file name follows the convention: `[SSSS][YY][MM].WTH`

- `SSSS` = 4-character station code (e.g., `UFGA`)
- `YY` = 2-digit year when the weather data begins
- `MM` = 2-digit month when the data begins (use `01` for January)

**Example**: `UFGA8201.WTH` = Gainesville, FL station, data starting from January 1982.

**For multi-year files**: Use the start year and month `01`. For example, data spanning 1982-1990 would still be named `UFGA8201.WTH` if it starts in January 1982.

**Y2K convention for the filename**:
- YY = 00-70 maps to 2000-2070
- YY = 71-99 maps to 1971-1999

**Decision rule**: If your data starts in year 2005, YY = `05`. If it starts in 1985, YY = `85`.

### Step 2: Write the Title Line

The first line of the file is a title/comment line starting with `*WEATHER DATA`:

```
*WEATHER DATA : Gainesville,Florida,USA
```

**Format**: `*WEATHER DATA :` followed by a space and free-form location description. This line is for documentation only; DSSAT does not parse it for data.

### Step 3: Leave a Blank Line

Insert one blank line after the title line. This is required by the parser.

### Step 4: Write the Station Header

```
@ INSI      LAT     LONG  ELEV   TAV   AMP REFHT WNDHT
  UFGA   29.630  -82.370    10  20.9  13.0  2.00  3.00
```

**Header variable definitions**:

| Variable | Width | Description | Units | Required |
|----------|-------|-------------|-------|----------|
| INSI | 6 | Station code (4 characters, left-justified within field) | -- | YES |
| LAT | 9 | Latitude | Decimal degrees (N positive, S negative) | YES |
| LONG | 9 | Longitude | Decimal degrees (E positive, W negative) | YES |
| ELEV | 6 | Elevation above sea level | Meters | YES (-99 if unknown) |
| TAV | 6 | Annual average ambient temperature | Degrees Celsius | YES (critical) |
| AMP | 6 | Annual amplitude of monthly mean temperature | Degrees Celsius | YES (critical) |
| REFHT | 6 | Reference height for weather measurements | Meters | Recommended (default 2.0) |
| WNDHT | 6 | Wind speed measurement height | Meters | Recommended (default 3.0) |

**Critical note on INSI**: The INSI code here must match the WSTA code used in the FileX *FIELDS section. A mismatch will cause DSSAT to fail to locate the weather data.

### Step 5: Calculate TAV (Annual Average Temperature)

TAV is the annual average of all daily mean temperatures.

**Procedure**:
1. For each day, compute daily mean temperature: `Tmean_i = (TMAX_i + TMIN_i) / 2.0`
2. Sum all Tmean values over the entire data period.
3. Divide by the number of days: `TAV = SUM(Tmean_i) / N_days`
4. Round to one decimal place.

**Example calculation**:
```
If you have 365 days of data:
TAV = SUM((TMAX_i + TMIN_i) / 2.0 for i = 1..365) / 365
```

**Failure mode**: If TAV is left as -99 or defaulted to an incorrect value (e.g., 20.0 when actual is 10.0), the soil temperature initialization will be wrong, producing incorrect soil N mineralization and water dynamics in the first days/weeks of simulation.

**Tool reference**: `calculate_tav_amp` -- invoke this tool with the daily temperature data to compute TAV and AMP automatically.

### Step 6: Calculate AMP (Annual Temperature Amplitude)

AMP is the amplitude of monthly mean temperature variation.

**Procedure**:
1. For each month, compute the monthly average of daily mean temperatures: `Tmean_month_j = AVG((TMAX_i + TMIN_i) / 2.0) for all days in month j`
2. Find the maximum monthly mean: `Tmax_month = MAX(Tmean_month_1, ..., Tmean_month_12)`
3. Find the minimum monthly mean: `Tmin_month = MIN(Tmean_month_1, ..., Tmean_month_12)`
4. Compute: `AMP = Tmax_month - Tmin_month`
5. Round to one decimal place.

**Example**:
```
If warmest monthly mean = 27.5 C (July) and coldest = 14.5 C (January):
AMP = 27.5 - 14.5 = 13.0
```

**Multi-year data**: If you have multiple years, calculate AMP for each year and average them. Alternatively, compute AMP from the long-term monthly means.

**Failure mode**: If AMP defaults to 5.0 (a common placeholder), soil temperature calculations will underestimate seasonal variation in temperate climates and overestimate it in tropical climates. This directly affects soil organic matter decomposition rates.

### Step 7: Write the Daily Data Header

```
@DATE  SRAD  TMAX  TMIN  RAIN               PAR
```

**Required columns**:

| Column | Variable | Width | Units | Description |
|--------|----------|-------|-------|-------------|
| 1 | DATE | 5 | YYDDD | Julian date |
| 2 | SRAD | 6 | MJ/m2/day | Daily solar radiation |
| 3 | TMAX | 6 | Degrees C | Maximum daily air temperature |
| 4 | TMIN | 6 | Degrees C | Minimum daily air temperature |
| 5 | RAIN | 6 | mm/day | Total daily precipitation |

**Optional columns** (add to header if available):

| Column | Variable | Width | Units | Description |
|--------|----------|-------|-------|-------------|
| 6 | WIND | 6 | km/day | Daily wind run |
| 7 | DEWP | 6 | Degrees C | Dewpoint temperature |
| 8 | PAR | 6 | moles/m2/day | Photosynthetically active radiation |
| 9 | RHUM | 6 | Percent | Relative humidity |

**Decision rule on optional variables**: Include WIND if the evapotranspiration method (MEEVP) is Penman-Monteith (F=FAO-56) or ASCE (Z), because these methods require wind data. If using Priestley-Taylor (P) or Ritchie (R), WIND is less critical. PAR is useful if measured; DSSAT can estimate it from SRAD if missing.

### Step 8: Format the YYDDD Date

The DATE field uses the YYDDD format:
- `YY` = Last two digits of the year
- `DDD` = Day of year (001-366)

**Y2K convention**:
- YY = 00-70 maps to years 2000-2070
- YY = 71-99 maps to years 1971-1999

**Examples**:
| Calendar Date | YYDDD |
|--------------|-------|
| January 1, 1982 | 82001 |
| December 31, 1982 | 82365 |
| February 29, 2000 (leap year) | 00060 |
| March 1, 2000 (leap year) | 00061 |
| January 1, 2025 | 25001 |

**Conversion procedure**:
1. Extract the year and compute the 2-digit year: `YY = year mod 100`
2. Determine if the year is a leap year: leap if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
3. Compute the day of year (DDD): January 1 = 001, January 31 = 031, February 1 = 032, etc.
4. Format as 5 characters: `YYDDD` (e.g., `82001`, zero-padded)

### Step 9: Write Daily Data Rows

Each row contains one day of weather data, with values in fixed-width columns matching the @-header.

```
82001   5.9  24.4  15.6  19.0              12.4
82002   7.0  22.2  15.0   0.0              14.2
82003   9.0  27.8  17.2   0.0              18.4
```

**Formatting rules**:
1. Each value occupies exactly the column width specified in the header.
2. Values are right-justified within their field.
3. Decimal precision: SRAD to 1 decimal, TMAX/TMIN to 1 decimal, RAIN to 1 decimal.
4. Missing values MUST be coded as `-99` (not NaN, not blank, not 0 unless truly zero).
5. Days MUST be in chronological order with no gaps. If a day is missing data, include the day row with `-99` for unknown values.

**Critical unit conversions**:

| Source Unit | DSSAT Unit | Conversion |
|-------------|-----------|------------|
| W/m2 (average daily) | MJ/m2/day (SRAD) | Multiply by 0.0864 (= 86400 seconds / 1,000,000) |
| cal/cm2/day (Langleys) | MJ/m2/day (SRAD) | Multiply by 0.04184 |
| kWh/m2/day | MJ/m2/day (SRAD) | Multiply by 3.6 |
| m/s (wind) | km/day (WIND) | Multiply by 86.4 (= 86400 / 1000) |
| mph (wind) | km/day (WIND) | Multiply by 38.624 (= 1.60934 * 24) |
| inches (rainfall) | mm/day (RAIN) | Multiply by 25.4 |
| Fahrenheit | Celsius (TMAX/TMIN) | (F - 32) * 5/9 |

**Decision rule for SRAD source verification**: SRAD typically ranges from 1-30 MJ/m2/day at the Earth's surface. If your values exceed 35 MJ/m2/day, you likely have the wrong units (e.g., W/m2 which ranges ~50-350). If values are < 0.5, you may have data in kWh/m2/day or another unit.

### Step 10: Handle Missing Values

**Rule**: Use `-99` (or `-99.` or `-99.0`) for any missing daily value.

**Specific handling**:

| Situation | Action |
|-----------|--------|
| SRAD missing for one day | Set to -99. DSSAT internal weather generator may fill it. |
| TMAX or TMIN missing | Set to -99. Critical variables -- more than 5 consecutive missing days will degrade results. |
| RAIN missing | Set to -99. Do NOT set to 0.0 as that implies no rainfall. |
| Entire day missing | Include the row with date and all values as -99. Do NOT skip the day. |
| NaN in source data | Replace with -99 before writing. NaN values will cause DSSAT to crash. |
| Negative SRAD | Set to -99 (SRAD cannot be negative). |
| TMIN > TMAX | Error in source data. Swap them if clearly a data entry error, or set both to -99 and note in metadata. |

### Step 11: Verify Date Sequence Continuity

After writing all daily rows, verify:

1. **No duplicate dates**: Each YYDDD value appears exactly once.
2. **No gaps**: Every consecutive day from the first to last date is present.
3. **Correct leap year handling**: Years divisible by 4 have 366 days (DDD goes to 366), others have 365.
4. **Year transitions**: The day after YY365 (or YY366 for leap years) is (YY+1)001.

**Verification command** (pseudocode):
```
for each pair of consecutive rows (row_i, row_{i+1}):
    expected_next = row_i.date + 1 day
    assert row_{i+1}.date == expected_next
```

**Failure mode**: Non-sequential dates cause DSSAT to read weather data out of order or skip simulation days. This produces silent errors in cumulative variables (rainfall totals, thermal time).

### Step 12: Validate the Complete File

Run these checks on the finished .WTH file:

1. **Header check**: First line starts with `*WEATHER DATA`.
2. **Station line check**: @INSI header is present and followed by one data line with LAT, LONG, ELEV, TAV, AMP.
3. **TAV range check**: TAV should be between -10 and 35 for most agricultural regions. Values outside this range are suspicious.
4. **AMP range check**: AMP should be between 1 and 30. Tropical locations: 1-8. Temperate: 10-25. Continental: 15-30.
5. **SRAD range check**: All non-missing SRAD values should be between 0.5 and 35.0 MJ/m2/day.
6. **Temperature range check**: TMAX should be between -50 and 60. TMIN should be between -60 and 50. TMIN must be <= TMAX for every day.
7. **RAIN range check**: RAIN should be >= 0 and typically < 500 mm/day (values > 300 are extreme and should be verified).
8. **Date continuity check**: No gaps, no duplicates.
9. **Column alignment check**: Spot-check 5 random rows to verify data falls in correct columns.
10. **Missing value check**: Count -99 values. More than 10% missing for any critical variable (SRAD, TMAX, TMIN, RAIN) warrants data infilling.

**Tool reference**: `validate_weather_file` -- invoke this tool with the .WTH file path to run automated validation checks.

## Expected Outputs

| Output | Format | Verification |
|--------|--------|--------------|
| .WTH file | `[SSSS][YY][MM].WTH` | File exists, parses without error |
| Title line | `*WEATHER DATA : ...` | Present as first line |
| Station header | LAT, LONG, ELEV, TAV, AMP populated | No -99 in TAV or AMP |
| Daily data | Continuous date sequence, correct units | SRAD in MJ/m2/d, RAIN in mm/d |
| File size | Approximately 30-40 bytes per daily row | 365 days ~ 11-15 KB |

## Validation Checks

1. **REQUIRED**: File starts with `*WEATHER DATA`.
2. **REQUIRED**: Station header line contains valid LAT (-90 to 90) and LONG (-180 to 180).
3. **REQUIRED**: TAV is not -99 and is within plausible range for the location.
4. **REQUIRED**: AMP is not -99 and is within plausible range.
5. **REQUIRED**: Daily data header (@DATE SRAD TMAX TMIN RAIN) is present.
6. **REQUIRED**: At least one complete year of daily data is present for the simulation period.
7. **REQUIRED**: No NaN, Inf, or non-numeric values in data columns.
8. **REQUIRED**: SRAD units are MJ/m2/day (not W/m2).
9. **REQUIRED**: WIND units are km/day (not m/s).
10. **REQUIRED**: Date sequence is continuous with no gaps.

## Common Pitfalls

1. **SRAD in wrong units (W/m2 vs MJ/m2/day)**: This is the single most common weather data error. Solar radiation from many station networks and reanalysis products is reported in W/m2 (average daily irradiance). DSSAT requires MJ/m2/day (daily total energy). Multiply W/m2 by 0.0864 to convert. If SRAD values are in the range 50-350, they are almost certainly in W/m2 and need conversion. Correct SRAD values typically range from 1-30 MJ/m2/day.

2. **WIND in m/s vs km/day**: Many weather stations report wind speed in m/s. DSSAT requires wind run in km/day. Multiply m/s by 86.4 to convert. If your wind values are in the range 0-15, they are likely in m/s. Correct DSSAT wind values are typically 50-500 km/day.

3. **NaN values silently masked**: If source data contains NaN (Not a Number) from Python/R processing, these must be explicitly replaced with -99 before writing to .WTH. DSSAT does not handle NaN and will crash or produce garbage results. Always check: `if value is NaN, replace with -99`.

4. **TAV/AMP defaulting to 20/5 if missing**: If TAV or AMP are left as -99 or omitted, some DSSAT versions silently default to TAV=20.0 and AMP=5.0. These defaults are only appropriate for tropical lowland locations. For temperate or cold climates, this causes grossly incorrect soil temperature initialization, affecting germination timing and N mineralization.

5. **Non-sequential dates**: Gaps in the date sequence (e.g., jumping from 82058 to 82060, skipping day 059) cause the weather reader to misalign data, assigning day 60's weather to day 59's simulation step. This error is silent and produces subtly wrong results. Always verify date continuity.

6. **Negative rainfall coded as 0**: If source data has -99 or negative values for rainfall (indicating missing data), do NOT replace them with 0.0. A value of 0.0 means "no rain fell," while -99 means "unknown." This distinction matters for water balance calculations.

7. **TMIN > TMAX on some days**: This indicates a data quality issue in the source. DSSAT will produce errors or unrealistic results. Check every day: if TMIN > TMAX, flag and correct before writing the .WTH file.

8. **Leap year errors**: February 29 must be included for leap years (DDD = 060 is Feb 29 in leap years, Mar 1 in non-leap years). Off-by-one errors in day-of-year calculation after February cause systematic date shifts for the rest of the year.

9. **Column alignment drift**: If one row has a RAIN value that is wider than expected (e.g., `999.9` where `99.9` was expected), it can push subsequent columns out of alignment. DSSAT reads by column position. Always format numbers to fit within the designated column width.

10. **Multi-year file boundary errors**: When data spans year boundaries (e.g., 82365 to 83001), ensure the YYDDD format correctly increments. The day after day 365 (or 366 in leap years) is day 001 of the next year. The 2-digit year must also increment.
