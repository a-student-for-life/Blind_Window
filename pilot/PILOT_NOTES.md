# Pilot notes

Run with `python -m study.pilot` (resumable; skips finished stages). Results per event in
`pilot/out/<event>/`, timings in `pilot/out/timings.jsonl`, overview in `pilot/out/PILOT_SUMMARY.md`.
Needs the accounts in `STUDY_SETUP.md` (`python -m study.creds`), the GloFAS threshold files in
`data/study/aux/` and the yearly SentiWiki plan ZIPs in `data/study/plans_archive/`. Go/no-go rule: `MANUAL_CHECK_10.md`.

To record here: per-event run time and Earth Engine requests; request fields that had to change
(EWDS, TIGGE, ASF); plan issue time from file names vs ZIP entry times; whether Guwahati 2024
reproduces the replay's 227.9 h; any rule in ANALYSIS_PLAN.md that the pilot showed cannot be
applied as written (proposed change goes to Janice before approval).
