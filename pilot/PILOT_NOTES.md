# Pilot notes

Run with `python -m study.pilot` (resumable; skips finished stages). Results per event in
`pilot/out/<event>/`, timings in `pilot/out/timings.jsonl`, overview in `pilot/out/PILOT_SUMMARY.md`.
Needs the accounts in `STUDY_SETUP.md` (`python -m study.creds`), the GloFAS threshold files in
`data/study/aux/` and the yearly SentiWiki plan ZIPs in `data/study/plans_archive/`. Go/no-go rule: `MANUAL_CHECK_10.md`.

To record here: per-event run time and Earth Engine requests; request fields that had to change
(EWDS, TIGGE, ASF); plan issue time from file names vs ZIP entry times; whether Guwahati 2024
reproduces the replay's 227.9 h; any rule in ANALYSIS_PLAN.md that the pilot showed cannot be
applied as written (proposed change goes to Janice before approval).

## Request fields that had to change (22 Nov 2026)

- EWDS `cems-glofas-historical`: `hyear/hmonth/hday` -> `year/month/day`; new field
  `timespan: time_mean`; variable `river_discharge_in_the_last_24_hours` ->
  `average_river_discharge_in_the_last_24_hours`. Needs two licences on the account: "Terms of use
  CEMS" and "CEMS-FLOODS datasets licence". Values are labelled by the end of the 24 h mean.
- EWDS `cems-glofas-forecast`: field names in `fetch.glofas_forecast_request` match the current form.
- TIGGE (ECDS `tigge-forecasts`, DEVIATIONS.md #1): field names taken from the ECDS form:
  `origin: ecmwf`, `forecast_type: perturbed_forecast`, `year/month/day`, `leadtime_hour`,
  `level_type: single_level`, `variable: total_cloud_cover`. No member choice (all 50 come back);
  GRIB only. Requests wait in a shared queue (the first P01 test waited over 40 minutes before starting).
- ASF search: unchanged, works as written.

## Plan archive (SentiWiki yearly ZIPs)

- 27 ZIPs (S1A/S1B "Acquisition-Segments", S2A/S2B "Acquisition-Plans", 2024 S2 spelt "Plants"),
  351 MB in total. Only plan files issued 60 days before to 30 days after a pilot search window were
  kept: 691 files in `data/study/plans_archive/plans_<year>.zip` (149 MB); the raw ZIPs were deleted.
- File names are inconsistent and most do not match `blindwindow.plans.NAME_RE` as they stand:
  `S1A_MP_USER_...` and `S2B_MP_ACQ__KML_...` match, but `Sentinel-1A_MP_...`, `Sentinel_1A_MP_...`,
  `Senitnel-1A_MP_...`, `Sentinel-2A-MP_ACQ_KML_...`, `Sentinel-2A-MP-ACQ-KML-...`, `Sentinel-2_MP_ACQ_KML_...`
  (no A/B) and bare `MP_ACQ__KML_...` (no satellite; most of S2 2022 and one S1A 2022 file) do not.
  Each kept file is therefore stored under a standard name (`S1A_MP_USER_<start>_<end>.kml`,
  `S2A_MP_ACQ__KML_<start>_<end>.kml`) that NAME_RE reads. The two timestamps are copied from the
  original name; the satellite comes from the name where present and otherwise from the yearly ZIP the
  file came from (25 of 691 files). Original names are in `data/study/plans_archive/plans_manifest.csv`.
  Open point: the 2017 S2A ZIP has `Sentinel-2_...` files with no A/B; they are counted as S2A here.
- Issue time in the name vs ZIP entry time: they agree only for 2017 S1A (38/38 within 2 days) and
  S1B (54/55). Every later ZIP has the entry times of when ESA built the archive (e.g. 5 May 2021 for
  all 2020 files), not of the plan, so the entry time cannot check the issue time after 2017. The
  first timestamp in the name is used as the issue time (ANALYSIS_PLAN.md section 6), as planned.

## GloFAS thresholds

- `flood_threshold_glofas_v4_rl_{2.0,5.0,10.0}.nc` from the ECMWF Confluence page "Auxiliary Data"
  (165 MB each, global 0.05 deg). Cropped to the study box plus 1 deg
  (`*_southasia_sea.nc`, 10.8 MB each) and the global files deleted.
- P01 cell (26.175, 91.725): 2-year 51,462, 5-year 59,746, 10-year 65,230 m3/s. GloFAS reanalysis
  peak 65,374 m3/s for 1 July 2024 (label 2 July), so above the 10-year level.
