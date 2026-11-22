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
