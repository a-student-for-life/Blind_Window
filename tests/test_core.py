"""Offline tests. Fixtures are hand-made test data, never shipped as results."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from blindwindow import flood, plans, predictor

FIX = Path(__file__).parent / "fixtures"
UTC = timezone.utc


def T(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


class Plans(unittest.TestCase):
    def test_name_regex(self):
        for name, sat in [("/documents/d/sentinel/s1d_mp_user_20261013t173113_20261102t193900", "s1d"),
                          ("S2A_MP_ACQ__KML_20240627T120000_20240715T150000.kml", "S2A"),
                          ("s2c_mp_acq__kml_20261015t120000_20261102t150000", "s2c")]:
            m = plans.NAME_RE.search(name)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1), sat)

    def test_parse_and_cluster(self):
        fps = plans.parse_kml((FIX / "plan_test.kml").read_bytes(), "S2B")
        self.assertEqual(len(fps), 3)
        self.assertEqual(fps[0]["mode"], "MSI")
        self.assertEqual(fps[2]["start"], T("2026-10-22T04:28:00"))
        p = plans.passes_over(fps, 26.175, 91.625)
        self.assertEqual(len(p), 1)                      # two footprints, one pass
        self.assertEqual(p[0]["kind"], "optical")
        self.assertEqual(plans.passes_over(fps, 10.5, 80.5)[0]["time"], T("2026-10-22T04:28:00"))

    def test_project_marks_and_dedups(self):
        base = [{"satellite": "S1C", "time": T("2026-10-20T00:00:00"), "kind": "sar", "mode": None, "source": "planned"}]
        out = plans.project(base, {"S1C": T("2026-10-25T00:00:00")}, T("2026-11-20T00:00:00"))
        times = [(p["time"], p["source"]) for p in out]
        self.assertIn((T("2026-11-01T00:00:00"), "projected"), times)
        self.assertIn((T("2026-11-13T00:00:00"), "projected"), times)
        self.assertEqual(len(out), 3)


class Flood(unittest.TestCase):
    def test_choose_cell(self):
        c = [{"lat": 1, "lon": 1, "max_m3s": 13.9}, {"lat": 2, "lon": 2, "max_m3s": 65312.0},
             {"lat": 3, "lon": 3, "max_m3s": None}]
        best, st = flood.choose_cell(c, 20000)
        self.assertEqual((best["lat"], st), (2, "ok"))
        self.assertEqual(flood.choose_cell(c[:1], 20000)[1], "below_min_peak")
        self.assertEqual(flood.choose_cell(c[2:], 20000)[1], "no_data")

    def test_summarize_forecast(self):
        daily = {"time": ["2026-10-15", "2026-10-16", "2026-10-17"],
                 "river_discharge": [100, 300, 200],
                 "river_discharge_member01": [100, 150, 400],
                 "river_discharge_member02": [500, 150, 100]}
        s = flood.summarize_forecast(daily)
        self.assertEqual((s["peak_date"], s["peak_m3s"]), ("2026-10-16", 300))
        self.assertEqual((s["member_peak_min"], s["member_peak_max"]), ("2026-10-15", "2026-10-17"))


class Predictor(unittest.TestCase):
    passes = [
        {"satellite": "S2A", "time": T("2024-07-04T04:26:59"), "kind": "optical", "source": "planned"},
        {"satellite": "S2B", "time": T("2024-07-09T04:26:57"), "kind": "optical", "source": "planned"},
        {"satellite": "S1A", "time": T("2024-07-11T11:54:23"), "kind": "sar", "source": "planned"},
    ]

    def test_guwahati_2024(self):
        """Reproduces the report: naive picks the cloudy S2A pass, cloud-aware picks S1A on July 11."""
        cloud = {T("2024-07-04T04:26:59"): 100, T("2024-07-09T04:26:57"): 95}
        r = predictor.predict("2024-07-01", self.passes, lambda t: cloud.get(t))
        self.assertEqual(r["peak_instant"], T("2024-07-02T00:00:00"))
        self.assertEqual(r["naive"]["satellite"], "S2A")
        self.assertAlmostEqual(r["naive"]["lag_h"], 52.4, places=1)
        self.assertEqual(r["cloud_aware"]["satellite"], "S1A")
        self.assertAlmostEqual(r["blind_window_h"], 227.9, places=1)
        # report: observed first usable 2024-07-11T11:57:15Z -> 227.95 h
        self.assertLess(abs(r["blind_window_h"] - 227.95), 0.1)

    def test_unknown_cloud_not_usable(self):
        r = predictor.predict("2024-07-01", self.passes, lambda t: None)
        self.assertEqual(r["cloud_aware"]["satellite"], "S1A")
        self.assertEqual(r["unresolved_optical_before"], 2)

    def test_clear_optical_wins(self):
        r = predictor.predict("2024-07-01", self.passes, lambda t: 10)
        self.assertEqual(r["cloud_aware"]["satellite"], "S2A")

    def test_beyond_horizon_and_brief(self):
        r = predictor.predict("2024-08-01", self.passes, lambda t: 100)
        self.assertTrue(r["beyond_horizon"])
        b = predictor.draft_brief({"name": "x"}, (26.175, 91.625), r, T("2024-07-25T00:00:00"))
        self.assertIn("DRAFT", b["status"])
        self.assertEqual(b["window_utc"][1], "beyond plan horizon")
        self.assertEqual(b["priority"], "urgent")

    def test_spread(self):
        s = predictor.spread([10, None, 30, 20, 40])
        self.assertEqual((s["n"], s["min"], s["median"], s["max"]), (4, 10, 30, 40))


class ReplayData(unittest.TestCase):
    def test_reanalysis_matches_report(self):
        s = json.loads((Path(__file__).parent.parent / "data" / "guwahati_2024_reanalysis.json").read_text())
        i = max(range(len(s["dates"])), key=lambda k: s["discharge_m3s"][k])
        self.assertEqual(s["dates"][i], "2024-07-01")
        self.assertEqual(s["valid_time_end"][i][:10], "2024-07-02")
        self.assertAlmostEqual(s["discharge_m3s"][i], 65373.9, places=1)


if __name__ == "__main__":
    unittest.main()
