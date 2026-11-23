# Pilot report: is the full study worth running?

Pilot of 10 events (P01–P10), run on 22–23 Nov 2026 on the laptop. Pilot events are excluded
from all main results (ANALYSIS_PLAN.md section 13). Raw outputs: `pilot/out/`, generated table:
`pilot/out/PILOT_SUMMARY.md`.

## Short answer

**Go, for RQ1 and RQ2.** Every step for the observed blind window and the plan check works end to
end, runs in seconds per event, and gives clear, plausible numbers.
**RQ3 (forecast test): RQ3_VERDICT**

## 1. What the pilot found

| Event | Peak | Days above 5-yr flow | First usable image after peak | Seen while flooded? | Usual blind window at this spot |
|---|---|---|---|---|---|
| P01 Brahmaputra, Guwahati | 1 Jul 2024 | 2 | S1, 228 h (9.5 days) | no | 60 h |
| P02 Godavari, lower reach | 26 Jul 2024 | 9 | S1, 168 h (7 days) | yes (before peak) | 101 h |
| P04 Kosi, Bihar | 13 Aug 2017 | 2 | S1, 156 h (6.5 days) | no | 60 h |
| P05 Jamuna, Bahadurabad | 12 Jul 2020 | 2 | S1, 12 h | yes | 84 h |

- **Only 4 of 10 pilot floods reach the 5-year flow** in GloFAS (P03, P07, P08, P10 reach the
  2-year flow only; P06 and P09 not even that). This is about how the pilot list was picked (well
  known floods, not GloFAS exceedances), not a bug. The main run finds events from GloFAS itself,
  so it is not affected, but it means many reported floods are "small" in GloFAS terms.
- **Sentinel-2 never gave a usable image** within 30 days of any peak except P05 (20 days later).
  Monsoon cloud. Every first usable image came from Sentinel-1.
- **3 of 4 floods were missed** (no usable image before the flow fell back below the 5-year level),
  and the blind window after these peaks was 2–4 times longer than usual for the same spot.
  This is the headline the study is built to test; 4 events prove nothing, but the signal is there.
- **Plans vs reality (RQ2):** PLANS_LINE

## 2. Forecast test (RQ3)

RQ3_SECTION

## 3. Time and size

| Step | Per event (median, pilot) | Notes |
|---|---|---|
| GloFAS flow record | 6.5 min (max 18.5) | download queue at Copernicus; one per river point, not per event |
| Floodplain point | 4 s | Earth Engine |
| Observed images | 5 s | Earth Engine |
| S1 records (ASF) | 1.5 s | |
| Plans | 7 s | plan archive downloaded once |
| Site climatology | 24 s | Earth Engine |
| Usual cloudiness | CLOUDCLIM_T | Earth Engine |
| GloFAS forecasts (3 per event) | FORECAST_T | download queue at Copernicus |

Downloads for 10 events: about 185 MB, so 800 events is roughly 15 GB passing through, but only
small tables are kept. That is why the main run goes to GitHub Actions, not the laptop.

**Scaling to the main run (cap 800 events):** SCALING

## 4. Things to fix or decide before the main run

1. **"Missed" is almost automatic.** Above the 5-year flow, three of four floods lasted only two
   days, so almost no satellite can see them in time. The plan's rule stays as approved, but you
   may want a second reading where the flood lasts while the flow is above the 2-year level.
   That would be an extra robustness line, logged as a plan change. Your choice.
2. **Floodplain point sits at the river edge.** All four points have height above river = 0 m and
   are a few hundred metres from the GloFAS river cell. They may be on a sandbar or the channel
   itself rather than the floodplain. Question 2 of your manual check (below) is where you confirm
   this; if they look wrong I'll tighten the rule (for example, at least 1 km from permanent water).
3. **Fixed during the pilot:** request field names at Copernicus, the ECMWF move of TIGGE, river
   cell picking the wrong channel (Kosi, Indus), forecast files arriving zipped, and Sentinel-2
   plan matching (it compared times to the start of a long planned strip). All logged in
   `pilot/PILOT_NOTES.md`; plan changes in `DEVIATIONS.md` (#1 TIGGE route, #2 usual cloudiness).

## 5. What you need to do: manual check (about 30 minutes)

`pilot/MANUAL_CHECK_10.md` has four questions per event: is it a real reported flood, is the
point on the floodplain, is the "first usable image" really clear over the point, and was no
earlier usable image missed. Only P01, P02, P04 and P05 get all four; the other six only get
question 1 (they never reached the 5-year flow). I'll send you a simple checking page with a map
link and the images for each event, so you only have to look and answer yes / no / can't tell.

The approved go/no-go rule ("questions 2–4 yes for 8 of 10") was written for 10 checkable
events; with 4, I'll read it as "yes for all 4, or each failure traced to a fixable bug".
