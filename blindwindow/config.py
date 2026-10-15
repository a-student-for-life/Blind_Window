"""River points and fixed rules. Edit this file to add or move points."""

# Seed coordinates are only starting points. Every point is snapped to the
# GloFAS cell that carries the main river before it is used (see flood.snap).
# min_peak_m3s guards against snapping to a tiny tributary or the wrong river:
# a snap whose largest discharge is below it is rejected and flagged.
RIVER_POINTS = [
    {"id": "guwahati", "name": "Brahmaputra at Guwahati", "lat": 26.175, "lon": 91.625, "min_peak_m3s": 20000},
    {"id": "malda", "name": "Ganges near Malda", "lat": 24.775, "lon": 87.925, "min_peak_m3s": 10000},
    {"id": "godavari", "name": "Godavari lower reach", "lat": 17.275, "lon": 81.675, "min_peak_m3s": 10000},
    {"id": "vijayawada", "name": "Krishna at Vijayawada", "lat": 16.500, "lon": 80.650, "min_peak_m3s": 3000},
    {"id": "trichy", "name": "Cauvery near Tiruchirappalli", "lat": 10.850, "lon": 78.700, "min_peak_m3s": 1000},
]

# Snapping uses a past monsoon window, because Open-Meteo's consolidated
# GloFAS series has no values for recent months (your run got 0 non-null
# values for 2025-10..2026-10, while 2024 worked).
SNAP_WINDOW = ("2024-06-01", "2024-10-31")
SNAP_GRID_STEP = 0.05
SNAP_GRID_HALF = 3          # 7x7 grid
SNAP_MODELS = ("consolidated_v4", "seamless_v4")

FORECAST_MODEL = "forecast_v4"
FORECAST_DAYS = 30

CLOUD_USABLE_BELOW = 30.0   # % — fixed rule, not tuned
CLUSTER_HOURS = 6
REPEAT_DAYS = {"S1": 12, "S2": 10}   # per-satellite repeat cycle, used only to project beyond the plan files
AOI_HALF_DEG = 0.25         # draft brief area: ~25 km box around the cell
HTTP_TIMEOUT = 40
