# How blind are we? Observed and forecast satellite blind windows after river flood peaks in South and Southeast Asia

Draft for Natural Hazards and Earth System Sciences (NHESS). Numbers marked **[R: …]** come from
`results/RESULTS.md` after `python -m study.analyse`; fill them in and delete the brackets.

## Abstract (≤ 250 words)

Free satellite imagery is the first look most responders get at a river flood, but the first
usable image can arrive days after the peak. We measure this "blind window" for **[R: N]** river
flood peaks on large rivers in South and Southeast Asia (2017–2024), defined from the GloFAS v4
reanalysis at the 5-year return level. The median time from peak to the first usable Sentinel-1
or cloud-free Sentinel-2 image of the floodplain was **[R: median] h**, and in **[R: missed %]** of
floods no usable image arrived before the flow fell back below the 5-year level. Sentinel-2 was
rarely usable during the monsoon. ESA's published acquisition plans, as available a day ahead,
contained **[R: S1 recall]** of the Sentinel-1 acquisitions that actually happened. A forecast that
combines the GloFAS forecast, the plans and the site's usual cloudiness, issued three days before
the peak, predicted the first usable image with a mean absolute error of **[R: MAE] h**, against
**[R: baseline MAEs] h** for three simple baselines (**[R: verdicts]**). Errors were dominated by
GloFAS peak timing. The analysis plan was fixed before any outcome was seen; all deviations are
reported.

## 1. Introduction

- Floods and satellites: Sentinel-1 (radar, cloud-independent, 12-day repeat per satellite; S1B
  lost Dec 2021) and Sentinel-2 (optical, 5-day repeat, cloud-limited). Rapid mapping services
  (Copernicus EMS, International Charter) depend on the first image.
- Gap: studies of revisit and latency are orbit-based or event case studies; none measures, over a
  large unbiased event set, how long after real flood peaks a usable image arrives, whether the
  public plans predict it, and whether it can be forecast.
- This study: three questions (RQ1 observed blind window, RQ2 plan completeness, RQ3 forecast
  skill), pre-registered plan, public code.

## 2. Data and methods

**2.1 Events.** GloFAS v4 reanalysis daily discharge; river cells with upstream area ≥ 10,000 km²,
thinned to one point per 50 km on the same river (outlet from the GloFAS drainage network);
lakes and reservoirs dropped; 16 countries of South and Southeast Asia. An event is a run of days
above the cell's 5-year return-period discharge, runs ≤ 7 days apart merged. Peak instant t0 =
end of the peak day. Point-events in the same HydroBASINS level-4 basin within 10 days form an
episode, the unit of all resampling. Exclusions: period edges, pilot events, plan-archive gaps
(RQ2/RQ3). Cap of 800 events (seeded, stratified by year). **[R: counts from events_summary.json]**

**2.2 Floodplain point and usable image.** Point on low, normally dry land next to the river cell
(JRC surface-water occurrence < 5%, MERIT Hydro HAND ≤ 5 m, not built-up). Usable: Sentinel-1 GRD
IW VV with ≥ 90% valid pixels within 500 m; Sentinel-2 L1C with ≥ 90% of pixels at s2cloudless
probability ≤ 40%. Blind window = hours from t0 to the first usable acquisition, censored at
720 h. "Missed" = first usable image after the end of the event.

**2.3 Plans (RQ2).** ESA Sentinel-1 and Sentinel-2 acquisition plans (SentiWiki archive),
judged as available ≥ 24 h before each pass; matched one-to-one to real acquisitions (Sentinel-1
from ASF datatake records, Sentinel-2 from the archive) when the acquisition falls in the planned
segment ± 10 min. Recall, precision and usable precision by mission and year.

**2.4 Forecast (RQ3).** Issued at 00 UTC, 3 days (main), 1 and 5 days before the observed peak,
using only information available then: GloFAS forecast ensemble median for the peak day; the
plans; the site's usual cloudiness (mean cloudy share of Sentinel-2 passes within ± 15 days of the
same date in other years; DEVIATIONS #2). First Sentinel-1 pass, or Sentinel-2 pass with expected
cloud < 30%, after the predicted peak. Baselines: next pass of any satellite; next Sentinel-1
pass projected from past acquisitions; site climatology of the blind window. Paired ΔMAE with
episode bootstrap (5,000), Holm correction, smallest useful gain 12 h. Random subset of 200 events
(DEVIATIONS #3).

**2.5 Placebo dates and human checks.** Two non-flood dates per event (same point and season,
another year, flow below the 2-year level). Blind event check of 100 events by two raters
(Cohen's kappa); image spot-check of 60 acquisitions.

## 3. Results

**3.1 Events.** **[R]** events at **[R]** points in **[R]** episodes; by year and country.

**3.2 Observed blind window (RQ1).** Survival curve (Fig. 1, `fig_rq1_survival.png`). Median
**[R]**; Sentinel-1 vs Sentinel-2; missed share; South vs Southeast Asia; placebo contrast
**[R]** (longer after floods = flood-time cloud).

**3.3 Plans vs acquisitions (RQ2).** Table from RESULTS.md. Pilot hint: the first image after
the peak was always a planned Sentinel-1 pass.

**3.4 Forecast (RQ3).** ΔMAE table; hit rate ± 12 h; leads 1 and 5 days; GloFAS peak-day error.
Pilot illustration: exact when the peak day was right (Brahmaputra 2024, Godavari 2024); 288 h
off when GloFAS forecast the Jamuna 2020 peak 4–11 days late.

## 4. Discussion

- What a responder can expect after a monsoon flood peak: radar, and usually days later.
- The plans are good enough to forecast the first radar pass; the hard part is the flood peak.
- Sentinel-1 constellation: one satellite from 2022 to the Sentinel-1C era; compare years.
- Limitations: GloFAS-defined floods (checked by the blind event check), floodplain point rule,
  cloud shadow not modelled, usable ≠ flood mapped, usual cloudiness instead of a weather forecast
  (DEVIATIONS #2), subset for RQ3.

## 5. Conclusions

**[3–4 sentences, after results.]**

## Code and data availability

Code, plan, deviations and result tables: GitHub repository a-student-for-life/Blind_Window
(archive on Zenodo at submission). Data are public (GloFAS/CEMS, Copernicus Sentinel via Earth
Engine, ASF, ESA SentiWiki).

## Author contributions, competing interests

**[fill in]**
