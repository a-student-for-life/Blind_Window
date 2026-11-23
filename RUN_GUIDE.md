# Running the study without help

Everything runs on the laptop from `C:\Users\Janice\Downloads\Floods\research\Blind_Window`.
Open **PowerShell** there and switch on the Python environment you used for the pilot, for example:

```
.venv\Scripts\Activate.ps1
```

Every command below can be stopped (close the window, laptop asleep) and started again: it
skips what is already finished. Keep the laptop on, plugged in and online while it runs.

| Step | Command | Time | What you get |
|---|---|---|---|
| 1. Find all floods | `python -m study.scan` | 1–3 days, unattended | `data/study/events_main.csv` (up to 800 floods), `rq3_sample.csv` (200), `events_summary.json` (counts) |
| 2. Satellite results | `python -m study.main` | about 1–2 days for 800 floods, plus about 4 days of forecast downloads for the 200 | `data/study/out/<event>/` |
| 3. Check progress any time | `python -m study.main --status` | seconds | how many floods have finished each step |
| 4. Tables and figures | `python -m study.analyse` | a minute | `results/RESULTS.md`, `results/fig_rq1_survival.png`, `results/events_results.csv` |
| 5. Human check sheet | `python -m study.checkpage --main` | seconds | `results/CHECK_SHEET_main.md` |

Step 4 can be run while step 2 is still going: it uses whatever has finished so far.

## If something goes wrong

- **A line says `error`**: run the same command again; most errors are a busy server. If the same
  flood fails three times, open `data/study/out/<event>/<step>.error.txt` and keep it for later.
- **"No space left"**: delete `data/study/cache/` (downloads only, everything needed is kept elsewhere).
- **Earth Engine or Copernicus says the key is wrong**: the key files in `C:\Users\Janice\` were
  set up in STUDY_SETUP.md. Never share or upload them.
- **Copernicus "request too large" / "cost limit"**: do not keep retrying (the account can be
  suspended). Stop and leave it.

## What not to change

The rules of the study are fixed in `ANALYSIS_PLAN.md` (approved 22 Nov 2026). Any change is
written in `DEVIATIONS.md` with its date and reason before results are looked at.
