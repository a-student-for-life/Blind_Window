# Deviations from ANALYSIS_PLAN.md

Each change to the approved plan, with its date and reason. Results are reported whatever they
show. Entries use this format:

```
## N. Short title, DD Mon YYYY

Agreed by Janice on DD Mon YYYY. What had been seen: ... What had not been seen: ...

**Old rule.** ...
**Problem.** ...
**New rule.** ...
**Effect.** ...
```

Plan version 1 approved on 22 Nov 2026.

## 1. TIGGE access route, 22 Nov 2026

Recorded on 22 Nov 2026, during the pilot smoke test, before any TIGGE data or any main-set
outcome had been retrieved. Only the pilot event P01 had been run, for Earth Engine and ASF.

**Old rule.** Section 2: TIGGE ECMWF ensemble total cloud cover, retrieved with the ECMWF Web
API key.

**Problem.** ECMWF moved TIGGE to the ECMWF Data Store (ECDS) on 27 May 2026. The old Web API
still accepts the login, but no longer grants TIGGE access, and its licence page is retired.

**New rule.** The same TIGGE fields (ECMWF ensemble, 00 UTC runs, total cloud cover, 6-hourly
steps to 15 days) are retrieved from the ECDS (`tigge-forecasts`) with an ECDS API key.

**Effect.** None on the analysis: same data, different download route.

## 2. Usual cloudiness instead of the TIGGE cloud forecast, 23 Nov 2026

Agreed by Janice on 23 Nov 2026. What had been seen: pilot observed blind windows, plan matches
and site climatology for the 10 pilot events; GloFAS forecasts for P01. What had not been seen:
any TIGGE cloud data, any forecast-test error, any main-set outcome.

**Old rule.** Section 7, Cloud: TIGGE ECMWF ensemble mean total cloud cover at the point,
interpolated to each S2 pass time, up to 15 days ahead.

**Problem.** Since late October 2026 the ECMWF Data Store queues TIGGE requests for many hours.
In the pilot a single one-date request waited more than 8 hours without starting, and a second one
was still queued the next morning. At one request per issue date the 800-event main run (about
2,400 issue dates) cannot finish before the study deadline of 15 Dec 2026, and ECMWF warns that
bulk resubmission can suspend the account.

**New rule.** The cloud expected for an S2 pass is the site's usual cloudiness: the mean cloudy
share (100 × (1 − clear share), section 5 rules) of the S2 passes over the same floodplain point
within ±15 days of the same day of the year, in the other study years (2017–2024, the event's year
left out). With fewer than 3 such passes the cloud is unknown and the pass is not counted as usable
(as beyond 15 days before). The same 30% threshold applies, and there is no 15-day horizon.
Everything else in section 7 is unchanged.

**Effect.** RQ3 now tests "plans + usual cloudiness" rather than "plans + cloud forecast". This
is a weaker version of the cloud-aware forecast, so a gain over the baselines is, if anything,
harder to show; a weather-forecast version is named as future work. Like baseline 3, later years
are used for early events; nothing from the event's own year is used.

## 3. Forecast test on a random subset, 23 Nov 2026

Agreed by Janice on 23 Nov 2026. What had been seen: the pilot results, including the forecast
test for P01, P02 and P05 (pilot events, excluded from the main results). What had not been seen:
any main-set event, outcome or forecast.

**Old rule.** Section 7: the forecast test runs on every main event from 15 Nov 2019 on, at leads
of 3 days (main) and 1 and 5 days (secondary).

**Problem.** Each GloFAS forecast is a separate download, and in the pilot each waited about
40 minutes in the Copernicus queue (requests for two dates at once were refused). With up to
800 events × 3 leads, the downloads would take about 33 days and end after the study deadline.

**New rule.** The forecast test runs on a random subset of 200 main events from its main sample
(section 3: peaks in June–October of 2020–2024), drawn with seed 20261122, stratified by year, at most one event per episode,
at L = 3 days. Leads 1 and 5 days run on the first 50 events of the same draw. The draw is made
from the event list alone, before any forecast or outcome is downloaded, and committed. If fewer
than 200 events qualify, all are used. RQ1 and RQ2 still use every main event.

**Effect.** Wider confidence intervals for RQ3 than with all events; no change to RQ1 and RQ2.

## 4. Country and basin lookup through Earth Engine, 23 Nov 2026

Recorded on 23 Nov 2026, while writing the event scan, before any main-set event was found.

**Old rule.** Section 3: the study countries are taken from Natural Earth 1:10m admin-0.

**Problem.** The scan already uses Earth Engine for the HydroBASINS level-4 basins; Natural Earth
would be one more file to download by hand.

**New rule.** Country of each river point from the US Department of State LSIB boundaries in Earth
Engine (`USDOS/LSIB_SIMPLE/2017`), basin from `WWF/HydroSHEDS/v1/Basins/hybas_4`. A river point
that falls outside every land polygon (some river mouths) is dropped, as before.

**Effect.** Small differences at disputed or coastal borders only; the count of points per
country is reported in `data/study/events_summary.json`.

## 5. No lake and reservoir mask, 23 Nov 2026

Recorded on 23 Nov 2026, before any main-set event was found. **Old rule.** Section 3: lake and
reservoir cells (GloFAS mask) are dropped. **Problem.** The GloFAS v4 auxiliary-data page offers
no lake or reservoir mask file. **New rule.** No mask is applied; river points are kept as found.
**Effect.** A few points may sit in reservoirs, where floods are regulated; the floodplain-point
rule (section 4, not permanent water) and the human checks limit this. Counted in the limitations.

## 6. Placebo dates for RQ1 only, 23 Nov 2026

Recorded on 23 Nov 2026, before any main-set outcome. **Old rule.** Section 9: placebo dates are
run through sections 5 and 7. **Problem.** Section 7 on placebo dates needs about 400 more GloFAS
forecast downloads (about 40 min each), which do not fit before the deadline (see #3).
**New rule.** Placebo dates are run through section 5 (RQ1 contrast) only. **Effect.** The check
"a forecast gain that appears only on placebo dates" is not made; stated as a limitation.

## 7. One whole-region request per year for the event scan, 23-24 Nov 2026

Recorded on 23-24 Nov 2026, before any main-set event was found (2 of 144 tile-year pieces
downloaded). **Old rule.** Section 3: the whole region is scanned; the code asked EWDS for one
10-degree tile and one year at a time (144 requests). **Problem.** Each EWDS request now waits
about 5-12 h in the queue whatever its size (a one-point, one-year test waited almost 3 h without
starting), so 144 requests would take about a month. Open-Meteo's copy of the GloFAS reanalysis was
tested as a faster route and rejected: it returned a neighbouring cell at 8 of the 10 pilot river
points. EWDS refuses 8 years for one tile ("request too large") but accepts one year for the whole
region, so its size limit counts days, not area. **New rule.** Same data and same extraction: one
request per year for the box covering all tiles (8 requests), years in a seeded random order (SEED);
each year file is cut into the per-tile series. If the scan is stopped at a cut-off date, events come
only from complete years (and complete tiles); the years used are reported (`events_summary.json`).
**Effect.** None if all 8 years arrive. Otherwise the event set covers a random subset of years,
reported as such.
