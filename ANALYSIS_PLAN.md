# How blind are we? Analysis plan

Observed and forecast satellite blind windows after river flood peaks in South and Southeast Asia.

Version 1, approved 22 Nov 2026, before any satellite acquisition, image or cloud forecast has
been pulled for the main event set. The git history of this file is the record of what was
decided before results existed. Any later change goes in `DEVIATIONS.md` with its date,
who agreed, what had and had not been seen, and its effect. Results are reported whatever they show.

Status: **approved by Janice on 22 Nov 2026**, with all seven defaults in the decisions table below.

Only the 10 pilot events (`pilot/`) may be run before approval. They are excluded from every
main result.

---

## Decisions taken at sign-off

Each was drafted with a default; Janice approved all seven defaults on 22 Nov 2026.

| # | Decision | Approved choice | Alternative not taken |
|---|---|---|---|
| D1 | Study area | S and SE Asia, 60–125° E, 11° S–37° N, land of the 16 countries in section 3 | South Asia only (smaller, closer to the Indian demo points) |
| D2 | Which rivers | GloFAS cells with upstream area ≥ 10,000 km², thinned to one point per 50 km of river | ≥ 5,000 km² (more events, more cells where S1 cannot resolve the river) |
| D3 | Flood threshold | GloFAS v4 5-year return-period threshold | 2-year (more, smaller events); 2- and 10-year are run as robustness either way |
| D4 | Main forecast lead | 3 days before the observed peak | 1 or 5 days (both reported as secondary) |
| D5 | Smallest useful gain | Forecast beats a baseline by ≥ 12 h mean absolute error | 6 h or 24 h |
| D6 | Event cap | If more than 800 events, a seeded random sample of 800 stratified by year | No cap (slower Earth Engine runs) |
| D7 | Second rater for the blind event check | Jordan, on the same 100 events | Janice only, with an automated second reading (weaker; reviewers questioned this in WAKE) |

---

## 1. Questions

**RQ1, observed blind window.** After a river flood peak, how long does it take before a public
satellite (Sentinel-1 or cloud-free Sentinel-2) delivers a usable image of the floodplain, and how
often has the flood already receded by then?

**RQ2, plan completeness.** How completely do ESA's published acquisition plans, as available
before the event, predict the Sentinel-1 and Sentinel-2 acquisitions that actually happened over
flood sites, and how many planned passes were not acquired?

**RQ3, forecast skill.** Does a blind-window forecast issued before the peak, using only the
GloFAS forecast, the ESA plans and the cloud forecast available at that time, predict when the
first usable image arrives better than three simple baselines?

**Hypotheses.**
- RQ1 is descriptive. The pre-specified contrast is flood peaks versus matched non-flood dates
  (section 9): the expectation is a longer blind window after floods, because floods come with
  cloud.
- RQ2 is descriptive, with plan recall and precision reported by mission and year.
- RQ3: the Blind Window forecast has a lower mean absolute error than each baseline. The
  conclusion rules are in section 8.

---

## 2. Data sources

| Source | Use | Access |
|---|---|---|
| GloFAS v4 reanalysis (CEMS EWDS `cems-glofas-historical`), daily, 0.05° | Event definition, peak, duration | EWDS API token |
| GloFAS v4 return-period thresholds (CEMS auxiliary data) | 2-, 5-, 10-year thresholds | EWDS / ECMWF Confluence download |
| GloFAS v4 forecasts (`cems-glofas-forecast`), archived from 5 Nov 2019, 51 members | RQ3 predicted peak | EWDS API token |
| GloFAS upstream area and river network (auxiliary) | River cells, thinning | EWDS / auxiliary download |
| ESA S1 and S2 acquisition-plan archive (SentiWiki document library, yearly ZIPs) | RQ2, RQ3 plans | Public, no login |
| ASF search API, Sentinel-1 RAW and GRD product records | RQ2 actual S1 datatakes | Public, no login |
| Earth Engine `COPERNICUS/S1_GRD` | S1 pixel validity at the point | Earth Engine project |
| Earth Engine `COPERNICUS/S2_HARMONIZED` (L1C) + `COPERNICUS/S2_CLOUD_PROBABILITY` | S2 acquisitions, cloud-free check | Earth Engine project |
| Earth Engine MERIT Hydro (HAND) and JRC Global Surface Water | Floodplain point | Earth Engine project |
| TIGGE, ECMWF ensemble total cloud cover (`tcc`), 00 UTC runs, 6-hourly steps to 15 days | RQ3 cloud forecast | ECMWF Web API key + TIGGE licence |
| Dartmouth Flood Observatory archive, ReliefWeb, news | Blind event check only | Public |

S2 surface reflectance (L2A) is not used: in Earth Engine it is incomplete over Asia for 2017–18.
L1C with the s2cloudless probability layer covers the whole period consistently.

Open-Meteo is not used for the study (it has no archived cloud forecasts before 2024 and its
GloFAS series had gaps). The live Blind Window app keeps using it.

---

## 3. Events

**Area.** Land in India, Pakistan, Bangladesh, Nepal, Bhutan, Sri Lanka, Myanmar, Thailand, Laos,
Cambodia, Vietnam, Malaysia, Indonesia, the Philippines, Timor-Leste and Brunei (Natural Earth
1:10m admin-0), between 60° and 125° E and 11° S and 37° N. China is left out: its Sentinel-2
coverage and plan footprints are not comparable, and few news sources are checkable.

**Period.** Peaks from 1 January 2017 to 31 December 2024 (RQ1, RQ2). RQ3 uses peaks from
15 November 2019 (GloFAS forecast archive starts 5 November 2019, plus 10 days for leads), and its
main sample is the monsoon months June to October of 2020 to 2024.

**River points.** GloFAS cells with upstream area ≥ 10,000 km² (D2). They are thinned greedily:
sort by upstream area, largest first; keep a cell unless a kept cell is within 50 km great-circle
distance and on the same river (same downstream outlet in the GloFAS network). Lakes and reservoir
cells (GloFAS lake/reservoir mask) are dropped.

**Exceedance and merging.** At each river point, a day is "above" when the daily mean discharge
of the reanalysis exceeds that cell's 5-year return-period threshold (D3). Runs of above days
separated by 7 days or fewer are one event.

- **Peak date:** the day of maximum discharge in the event. Ties: the earliest.
- **Peak instant t0:** the end of the peak day (next day 00:00 UTC). This follows the GloFAS
  valid-time convention already used in `blindwindow/predictor.py`.
- **Onset:** the first above day (start of the day). **End:** the end of the last above day.
- **Duration:** End minus onset, in hours, from GloFAS only. Flood maps derived from Sentinel-1
  (for example GFM) are not used for duration, because they would make the outcome depend on
  the same satellites being studied.

**One flood, many points.** Points on the same river flood together. Each point-event is a row,
but all uncertainty is computed by resampling **flood episodes**: point-events in the same
HydroBASINS level-4 basin whose peaks fall within 10 days of each other belong to the same
episode (single-linkage on peak dates).

**Exclusions,** each counted and reported:

1. The peak falls within 30 days of the start or end of the period (window not fully observed).
2. No floodplain point can be found (section 4).
3. The point lies in a known S1 or S2 plan-archive gap (S1B 4–25 July 2017; S1A 12–26 April 2017)
   for RQ2 and RQ3 only. RQ1 keeps these events, because it uses actual acquisitions, not plans.
4. Pilot events (`pilot/pilot_events.json`): any point-event within 50 km and 7 days of a pilot
   event is excluded from all main results.

**Cap.** If more than 800 point-events remain, a random sample of 800 is drawn, stratified by year,
with seed 20261122 (D6). The draw is done before any outcome is pulled and committed as
`data/study/events_main.csv`.

---

## 4. Floodplain point

The GloFAS cell holds the river channel, which is permanent water and always looks "wet" to radar.
The point that is checked for images is on the floodplain next to the channel:

- Search the 3 × 3 block of GloFAS cells centred on the river cell (about 15 × 15 km).
- Candidates: 30 m pixels with JRC Global Surface Water occurrence < 5% (not permanent water) and
  MERIT Hydro HAND ≤ 5 m (low enough to flood), outside urban land (ESA WorldCover 2020 class 50).
- Choose the candidate with the lowest HAND; ties go to the one nearest the river cell centre.
- If no candidate exists, the event is excluded (exclusion 2).

The point is fixed per river point, not per event, so all events at a site share one floodplain
point. It is computed before any image is checked.

---

## 5. Usable image and observed blind window

**Area checked:** a 500 m radius around the floodplain point.

**Sentinel-1 usable** (`COPERNICUS/S1_GRD`, IW mode, VV band present): at least 90% of pixels in
the area are valid (not masked, not border noise). Each acquisition (one satellite, one pass) counts
once; adjacent slices of the same pass are mosaicked.

**Sentinel-2 usable** (L1C + s2cloudless): at least 90% of pixels in the area have cloud
probability ≤ 40% and are not masked. Cloud shadow is not modelled (a stated limitation, checked by
the image spot-check in section 10).

**Satellites in scope:** S1A, S1B (until its failure on 23 December 2021), S2A, S2B. Commercial
satellites and Landsat are out of scope ("public satellites" means the Copernicus Sentinels whose
plans ESA publishes). Landsat 8/9 are reported in one robustness check.

**Observed blind window** for an event: time from t0 to the start time of the first usable
acquisition after t0, in hours. Reported for S1 only, S2 only, and either. Searched up to 30 days
after t0; beyond that it is right-censored at 720 h.

**Missed flood:** the first usable acquisition (either mission) comes after the event End.

**Secondary outcomes:**
- **Seen during the flood:** any usable acquisition between onset and End, including the rising limb.
- **Seen near the peak:** a usable acquisition within ±24 h of t0.

**Summaries:** median and interquartile range of the blind window; share missed; Kaplan–Meier
curve of time to first usable image (handles censoring); all with 95% episode-bootstrap intervals
(5,000 resamples, seed 20261122). Split by mission, year, region (South Asia vs Southeast Asia),
monsoon (June–October) vs off-season, and S1B era (before vs after 23 December 2021).

---

## 6. Plans against acquisitions (RQ2)

**Plan available at time t.** A plan file is available at t if its issue time is at or before t.
The issue time is the first timestamp in the file name. The pilot checks this against the
modification times inside the archive ZIPs; if they disagree by more than a day, the later of the
two is used and recorded in `DEVIATIONS.md`.

**Planned pass over a point.** A plan segment whose polygon contains the floodplain point, using
`plans.parse_kml`, `plans.contains` and `plans.passes_over` (passes clustered within 6 h per
satellite). For each event window (t0 − 10 days to t0 + 30 days), the plan used is, for each
moment, the latest one available 24 h before it.

**Actual acquisition.**
- S1: matched at the **datatake level**, using ASF RAW product records (start, stop, footprint),
  not GRD footprints, because a GRD slice can miss a point that the datatake covered (seen for
  Guwahati, July 2019).
- S2: L1C granules in Earth Engine whose footprint contains the point.

**Matching.** A planned pass and an actual acquisition match when they are from the same
satellite and their times differ by no more than 10 minutes.

**Measures,** by mission and year:
- **Plan recall (completeness):** share of actual acquisitions over the point that were planned.
- **Plan precision:** share of planned passes that were acquired.
- **Usable precision:** share of planned passes that gave a usable image (section 5).
- The planned blind window (first planned usable pass, using actual cloud for S2) against the
  observed one, for events where they differ: how often the true first image was unplanned.

---

## 7. Forecast test (RQ3)

**Issue time τ.** 00 UTC on the day L days before the observed peak day, main L = 3 (D4);
secondary L = 1 and 5. Only data available at τ is used.

**Inputs at τ.**
- **Peak:** the GloFAS forecast issued at τ. The predicted peak date is the day of maximum of the
  ensemble median within the 30-day horizon.
- **Passes:** the plans available at τ (section 6), extended beyond each plan's end by the repeat
  cycle (`plans.project`: 12 days S1, 10 days S2).
- **Cloud** (replaced by usual cloudiness at the point, DEVIATIONS.md #2): TIGGE ECMWF ensemble mean total cloud cover at the point, linearly interpolated to each
  S2 pass time, up to 15 days ahead. Beyond 15 days an S2 pass is "unknown" and is not counted as
  usable (the existing rule in `predictor.py`).
- **Rule:** `predictor.predict` unchanged: first S1 pass, or first S2 pass with forecast cloud below
  30%, after the predicted peak instant.

**Target.** T_obs, the observed start time of the first usable acquisition after the observed
peak instant (section 5). Each forecast gives a predicted time T̂.

**Error.** |T̂ − T_obs| in hours, capped at 720 h. Events whose observed blind window is censored
are kept with T_obs at t0 + 720 h.

**Baselines,** all using the same predicted peak, so the comparison isolates passes and cloud:
1. **Next pass, any satellite:** the first planned or projected pass after the predicted peak,
   ignoring cloud (the `naive` output of `predictor.predict`).
2. **Next Sentinel-1 pass:** without plans. The S1 acquisitions over the point in the 36 days
   before τ (ASF records, as in TARS-triage `experiments/revision/latency_availability.py`),
   projected forward by 12 days per satellite; the first after the predicted peak.
3. **Site climatology:** predicted peak instant plus the median observed blind window at the same
   river point for start dates in the same calendar month in other years (2017–2024, leaving out
   the event's year), computed with the section 5 rules on every 3rd day.

**Main test.** For each baseline b, ΔMAE_b = MAE_b − MAE_BlindWindow at L = 3 days.
95% intervals and two-sided p-values from 5,000 episode-bootstrap resamples (paired, the same
resamples for all baselines). Holm correction across the three baselines, family-wise α = 0.05.

**Secondary.** Hit rate within ±12 h; ΔMAE at L = 1 and 5; an "oracle peak" run that uses the
observed peak, to separate peak-timing error from pass and cloud error; skill at predicting a
missed flood (predicted blind window longer than the forecast flood duration), reported as hit
rate and false-alarm rate.

---

## 8. How results are read (decided now)

For RQ3, per baseline:

| Result | Conclusion |
|---|---|
| Holm-adjusted p < 0.05 and ΔMAE ≥ 12 h (D5) | Blind Window beats that baseline by a useful margin |
| Upper end of the 95% interval below 12 h | No useful gain over that baseline (an informative null) |
| Anything else | Inconclusive for that baseline, reported with its interval |

The paper reports the result against "next Sentinel-1 pass" prominently whatever it is, because
in the monsoon the forecast rule often reduces to it (as found in the 2024 replay).

For RQ1 and RQ2 no threshold is set; they are estimates with intervals.

---

## 9. Placebo dates

For every main point-event, two non-flood dates at the same river point: same day of year ±15 days,
in a different year of 2017–2024, with discharge below the 2-year threshold for the 7 days on
either side, chosen at random with seed 20261122. Each placebo date is treated as a "peak" and
run through sections 5 and 7 unchanged.

- **RQ1 contrast:** paired difference in blind window (flood minus placebo), episode bootstrap.
- **RQ3:** ΔMAE on placebo dates is reported beside the flood result. A forecast gain that appears
  only on placebo dates would mean the gain comes from ordinary pass timing, not from flood-time
  cloud.

---

## 10. Human checks

**Blind event check** (Janice, with Jordan as second rater, D7). 100 main point-events drawn at
random (seed 20261122, stratified by year, at most one per episode). Each rater sees only the
river, country, place name, peak date and the GloFAS hydrograph, never any satellite information.
Question: "Is there a report (DFO, ReliefWeb or news) of river flooding within 50 km of this place
within 7 days of this date?" Yes / No / Can't tell. Written rules in `rules/EVENT_CHECK_RULES.md`
before the review starts. Agreement: Cohen's kappa with bootstrap interval
(`WAKE gap_checks/second_rater_agreement.py`).

- Reported: share confirmed, with interval.
- Main analysis uses all GloFAS-defined events. Robustness: only events confirmed by both raters.
- If fewer than 50% are confirmed, the paper describes events as "GloFAS high flows" rather than
  floods; that wording rule is decided now.

**Image spot-check** (Janice). 40 acquisitions classed usable (20 S1, 20 S2) and 20 classed not
usable (10 each), drawn at random, shown without the automatic label. Questions: is the area
covered with valid, cloud-free data; is flood water visible near the point. Reported: agreement
with the automatic rule; share of usable images showing flood water (descriptive).

---

## 11. Robustness checks

2- and 10-year thresholds; 3- and 14-day merge; upstream area ≥ 50,000 km²; 250 m and 1 km
radius; 80% and 95% valid-pixel share; cloud probability 20% and 60%; S2 forecast cloud threshold
20% and 50%; monsoon vs off-season; South vs Southeast Asia; before and after the S1B failure;
confirmed events only; Landsat 8/9 added as a usable source (RQ1); and, for RQ3, the full
2019-11 to 2024 period instead of the monsoons only.

No threshold is set for these. They are reported as checks on whether the main results depend on
the choice.

---

## 12. Known limitations, stated in advance

- Events are conditioned on a flood that happened; the forecast test does not measure false alarms
  (the placebo dates only partly address this).
- GloFAS discharge is a model; a 5-year exceedance in GloFAS is not always a flood on the ground
  (hence the blind check).
- "Usable" means a valid, cloud-free view of the floodplain point, not that flood water was mapped.
- The plan archive has gaps in 2017; plans for commercial and Landsat missions are not studied.
- One point per site: a nearby part of the floodplain may have been seen earlier.

---

## 13. Pilot

10 events, listed in `pilot/pilot_events.json`, run end to end to debug the pipeline and to time
it. The pilot may change implementation details (recorded in `DEVIATIONS.md` if they touch a rule
here), but no pilot result is used in any main estimate. A go/no-go note goes in
`pilot/PILOT_NOTES.md`, and the 10-event manual check in `pilot/MANUAL_CHECK_10.md`.

---

## 14. Reuse

Pure functions reused unchanged: `blindwindow.predictor` (rule), `blindwindow.plans.parse_kml`,
`contains`, `passes_over`, `project`. Patterns adapted from WAKE: event-level bootstrap and Holm
(`stage_b/analyse.py`), placebo dates (`stage_b/build_events.py`), the blind review page
(`review_page/`), Zenodo and citation files.
