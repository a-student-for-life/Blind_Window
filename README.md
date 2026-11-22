# Blind Window

Predicts when public satellites will next give a usable view of a forecast river flood, how long the blind window is, and drafts an observation brief a planner could review.

- **Live outlook:** today's GloFAS forecast, ESA Sentinel-1/2 plans and cloud forecasts for 5 Indian river points.
- **Replay:** the July 2024 Brahmaputra flood, as the system would have seen it 1 to 5 days before the peak.
- **Evidence:** the three 2024 events, including the Godavari failure case, plus limits.

## Retrospective study (in progress)

`study/` holds the pipeline for the paper *How blind are we? Observed and forecast satellite blind
windows after river flood peaks*. Start with `ANALYSIS_PLAN.md` (draft, awaiting approval),
`DEVIATIONS.md`, `STUDY_SETUP.md` (accounts) and `pilot/` (10 pilot events, excluded from results).
The live app below is reused by the study and is not changed by it.

```
python -m unittest tests.test_study tests.test_core   # offline, no accounts needed
python -m study.creds                                  # check EWDS, ECMWF and Earth Engine setup
```

## Run it

Needs Python 3.10+ and internet. No extra packages: the pipeline uses only the standard library.

```
cd blind-window
python -m unittest -v tests.test_core     # offline tests, should all pass
python -m blindwindow.run                 # live run, about 1 to 3 minutes
```

Open `outputs/blind_window.html` in a browser.

Other commands:

```
python -m blindwindow.run --only guwahati      # one point
python -m blindwindow.run --resnap             # redo river snapping
python -m blindwindow.run --render             # re-render from outputs/latest.json, no internet
```

For the demo, run it once before you present and use `--render` afterwards, so the page never depends on a live server.

## Design notes

1. **Snapping now works.** It scans a 7x7 grid over the 2024 monsoon (where `consolidated_v4` has data), not the last 365 days (which returned only nulls). Each point has a minimum peak (`config.py`), so a tributary cell is rejected instead of silently used. Snaps are cached in `data/snaps.json`.
2. **Forecasts use the snapped cell**, not the raw seed coordinate.
3. **The one-day date mismatch is explained.** EWDS labels a daily mean by the end of the 24 hours (valid time July 2); Open-Meteo by its start (July 1). Same value. Lags are measured from the end of the peak day, matching the report.
4. **Plan horizon.** Beyond a plan file's end, passes are projected from the repeat cycle (12 days for Sentinel-1, 10 for Sentinel-2) and drawn as hollow markers. They are never mixed up with planned passes.
5. **Ensemble spread.** The blind window is computed for every ensemble member's peak date, giving a range, not a probability.
6. **Prospective log.** Each run appends its predictions to `outputs/prospective_log.jsonl`, so they can be scored once the dates pass.

## Files

| Path | What |
|---|---|
| `blindwindow/config.py` | River points, thresholds, windows. Edit points here. |
| `blindwindow/flood.py` | Snapping and 30-day ensemble forecast (Open-Meteo Flood API). |
| `blindwindow/plans.py` | ESA plan discovery, KML/KMZ parsing, point intersection, projection. |
| `blindwindow/cloud.py` | Hourly cloud forecast (16 days max). |
| `blindwindow/predictor.py` | The rule: naive vs cloud-aware, member spread, draft brief. Pure functions. |
| `blindwindow/run.py` | Builds the snapshot, log, and page. |
| `data/replay_2024.json` | 2024 evidence, transcribed from `SMOKE_TEST_REPORT.md`. |
| `data/guwahati_2024_reanalysis.json` | Daily discharge from the cached EWDS GRIB (matches the report: 65,373.92 m³/s). |

## Test status

- 11 offline tests pass, including one that reproduces the report's Guwahati result (naive 52.4 h, cloud-aware 227.9 h vs observed 227.95 h).
- A full pipeline run with mocked responses rendered the page in headless Chrome with no JavaScript errors, on desktop and phone widths.
- **Not yet done:** a full live run against the real data servers.

## If the live run fails

Errors are shown on the page and in the terminal, never filled in. Likely ones:

- **`snap below_min_peak`:** the grid didn't reach the main river. Move the seed in `config.py` closer to the river channel, or widen `SNAP_GRID_HALF`.
- **Plan discovery finds nothing:** ESA may have changed its page layout. Check `plans.NAME_RE` against a link on the acquisition-plans page.
- **KML parses 0 footprints:** the time field may have a different name. Open the KML and adjust `plans.parse_kml`.

## Limits to say out loud

One fully validated event. Godavari shows plans miss real acquisitions, so planned passes are a lower bound. Cloud is a point forecast. "Usable" means a chance of a valid view, not flood detection. Large rivers only. The brief is a draft and is never submitted anywhere.
