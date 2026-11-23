"""Fixed parameters of the study, copied from ANALYSIS_PLAN.md (version 0, draft).

Change a value here only together with the plan (before approval) or with a DEVIATIONS.md entry
(after approval). Robustness variants are listed next to the main value and never replace it.
"""

SEED = 20261122

# Section 3: area and period
BBOX = (60.0, -11.0, 125.0, 37.0)          # lon0, lat0, lon1, lat1
COUNTRIES = ["IND", "PAK", "BGD", "NPL", "BTN", "LKA", "MMR", "THA", "LAO", "KHM", "VNM",
             "MYS", "IDN", "PHL", "TLS", "BRN"]
PERIOD = ("2017-01-01", "2024-12-31")
EDGE_DAYS = 30                               # exclusion 1
RQ3_START = "2019-11-15"
RQ3_MAIN_YEARS = (2020, 2024)
RQ3_MAIN_MONTHS = (6, 7, 8, 9, 10)

# Section 3: rivers and events
MIN_UPSTREAM_KM2 = 10_000                    # robustness: 50_000
THIN_KM = 50
RETURN_PERIOD = 5                            # robustness: 2, 10
MERGE_DAYS = 7                               # robustness: 3, 14
EPISODE_DAYS = 10
EVENT_CAP = 800
PILOT_EXCLUSION_KM = 50
PILOT_EXCLUSION_DAYS = 7

# Known plan-archive gaps (exclusion 3, RQ2 and RQ3 only), inclusive UTC dates
PLAN_GAPS = {"S1B": [("2017-07-04", "2017-07-25")], "S1A": [("2017-04-12", "2017-04-26")]}
S1B_FAILURE = "2021-12-23"

# Section 4: floodplain point
GSW_MAX_OCCURRENCE = 5        # %
HAND_MAX_M = 5
WORLDCOVER_URBAN = 50

# Section 5: usable image
RADIUS_M = 500                # robustness: 250, 1000
MIN_VALID_SHARE = 0.90        # robustness: 0.80, 0.95
S2_CLOUD_PROB_MAX = 40        # robustness: 20, 60
SEARCH_DAYS = 30
CENSOR_H = 720

# Section 6: plans vs acquisitions
PLAN_LEAD_H = 24
MATCH_TOL_MIN = 10
RQ2_WINDOW = (-10, 30)        # days around t0

# Section 7: forecast test
LEAD_DAYS_MAIN = 3
LEAD_DAYS_SECONDARY = (1, 5)
CLOUD_FORECAST_MAX_H = 15 * 24        # TIGGE only (not used since deviation 2)
CLOUD_SOURCE = "climatology"          # deviation 2: usual cloudiness instead of TIGGE
CLOUD_CLIM_HALF_DAYS = 15              # +/- days of year around each S2 pass
CLOUD_CLIM_MIN_PASSES = 3              # fewer past S2 passes -> cloud unknown (not usable)
CLOUD_CLIM_WINDOW = (-25, 50)          # days around the peak fetched in each other year
S2_CLOUD_FORECAST_USABLE_BELOW = 30.0   # same as blindwindow.config.CLOUD_USABLE_BELOW
NEXT_S1_LOOKBACK_DAYS = 36
CLIMATOLOGY_STEP_DAYS = 3
HIT_TOL_H = 12

# Section 8: reading the results
MIN_USEFUL_GAIN_H = 12
ALPHA = 0.05
N_BOOT = 5000

# Section 9: placebo dates
PLACEBO_PER_EVENT = 2
PLACEBO_DOY_WINDOW = 15
PLACEBO_CLEAR_DAYS = 7
PLACEBO_MAX_RP = 2
