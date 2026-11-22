"""Offline tests for the study pipeline's pure functions. Hand-made data only."""
import unittest
from datetime import date, datetime, timedelta, timezone

from study import baselines, events, guard, hindcast, observed, plan_match, scoring

UTC = timezone.utc


def T(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def days(start, n):
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


class Events(unittest.TestCase):
    def test_merge_within_7_days(self):
        q = [1, 5, 6, 1, 1, 1, 1, 1, 1, 1, 9, 1, 1, 1, 1, 1, 1, 1, 1, 7]
        ev = events.detect_events(days("2020-07-01", len(q)), q, 4)
        # runs at idx 1-2 and 10 are 7 days apart (gap of 7 below days) -> merged; idx 19 is 8 apart
        self.assertEqual(len(ev), 2)
        self.assertEqual(ev[0]["onset"], date(2020, 7, 2))
        self.assertEqual(ev[0]["end"], date(2020, 7, 11))
        self.assertEqual(ev[0]["peak_date"], date(2020, 7, 11))
        self.assertEqual(ev[0]["n_above"], 3)
        self.assertEqual(ev[1]["peak_date"], date(2020, 7, 20))

    def test_peak_tie_earliest_and_missing(self):
        q = [None, 8, 8, None, 3]
        ev = events.detect_events(days("2020-07-01", 5), q, 4)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["peak_date"], date(2020, 7, 2))

    def test_instants(self):
        i = events.instants({"onset": date(2024, 6, 28), "end": date(2024, 7, 5), "peak_date": date(2024, 7, 1)})
        self.assertEqual(i["t0"], T("2024-07-02T00:00:00"))     # same convention as predictor.peak_instant
        self.assertEqual(i["end"], T("2024-07-06T00:00:00"))

    def test_thin_points(self):
        cells = [{"lat": 26.0, "lon": 91.0, "upstream_km2": 500000, "outlet": "A"},
                 {"lat": 26.1, "lon": 91.1, "upstream_km2": 490000, "outlet": "A"},   # 15 km, same river
                 {"lat": 26.1, "lon": 91.1, "upstream_km2": 20000, "outlet": "B"},    # other river
                 {"lat": 27.0, "lon": 91.0, "upstream_km2": 9000, "outlet": "C"},     # too small
                 {"lat": 20.0, "lon": 91.0, "upstream_km2": 90000, "outlet": "A", "lake": True}]
        kept = events.thin_points(cells)
        self.assertEqual([(c["outlet"], c["upstream_km2"]) for c in kept], [("A", 500000), ("B", 20000)])

    def test_episodes(self):
        evs = [{"basin": 1, "peak_date": "2020-07-01"}, {"basin": 1, "peak_date": "2020-07-09"},
               {"basin": 1, "peak_date": "2020-07-18"}, {"basin": 1, "peak_date": "2020-08-30"},
               {"basin": 2, "peak_date": "2020-07-01"}]
        ids = events.episodes(evs)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(ids[1], ids[2])             # single linkage: 9 days from the previous
        self.assertNotEqual(ids[2], ids[3])
        self.assertNotEqual(ids[0], ids[4])

    def test_plan_gap_and_pilot(self):
        self.assertTrue(events.in_plan_gap(T("2017-07-10T00:00:00"), "S1B"))
        self.assertFalse(events.in_plan_gap(T("2017-07-26T00:00:00"), "S1B"))
        p = [{"lat": 26.175, "lon": 91.725, "peak_date": "2024-07-01"}]
        self.assertTrue(events.near_pilot({"lat": 26.3, "lon": 91.9, "peak_date": "2024-07-05"}, p))
        self.assertFalse(events.near_pilot({"lat": 26.3, "lon": 91.9, "peak_date": "2024-07-15"}, p))


class Observed(unittest.TestCase):
    inst = {"onset": T("2024-06-28T00:00:00"), "t0": T("2024-07-02T00:00:00"), "end": T("2024-07-06T00:00:00")}

    def test_blind_window(self):
        acq = [{"time": T("2024-06-30T12:00:00"), "mission": "S1", "usable": True},
               {"time": T("2024-07-03T04:30:00"), "mission": "S2", "usable": False},
               {"time": T("2024-07-08T00:00:00"), "mission": "S1", "usable": True}]
        r = observed.blind_window(self.inst, acq)
        self.assertEqual(r["bw_any_h"], 144.0)
        self.assertTrue(r["censored_s2"])
        self.assertEqual(r["bw_s2_h"], 720)
        self.assertTrue(r["missed"])                 # first usable after End
        self.assertTrue(r["seen_during_flood"])      # rising limb image counts here
        self.assertFalse(r["seen_near_peak"])

    def test_group_passes(self):
        ms = int(T("2024-07-03T04:30:00").timestamp() * 1000)
        rows = [{"t_ms": ms, "satellite": "S2A", "v": 0.5}, {"t_ms": ms + 60000, "satellite": "S2A", "v": 0.95},
                {"t_ms": ms, "satellite": "S1A", "v": 0.2}]
        g = observed.group_passes(rows)
        self.assertEqual(len(g), 2)
        self.assertTrue(next(a for a in g if a["satellite"] == "S2A")["usable"])


class PlanMatch(unittest.TestCase):
    def test_available_and_match(self):
        plans = [{"satellite": "S1A", "issued": T("2020-07-01T00:00:00")},
                 {"satellite": "S1A", "issued": T("2020-07-09T12:00:00")}]
        self.assertEqual(plan_match.plan_available(plans, T("2020-07-10T00:00:00"))["S1A"]["issued"],
                         T("2020-07-01T00:00:00"))  # second one is < 24 h old
        planned = [{"satellite": "S1A", "time": T("2020-07-12T00:00:00")},
                   {"satellite": "S1A", "time": T("2020-07-24T00:00:00")}]
        actual = [{"satellite": "S1A", "time": T("2020-07-12T00:05:00"), "usable": True},
                  {"satellite": "S1B", "time": T("2020-07-18T00:00:00"), "usable": True}]
        c = plan_match.completeness(planned, actual)
        self.assertEqual((c["n_matched"], c["recall"], c["precision"]), (1, 0.5, 0.5))
        self.assertEqual(c["unplanned"][0]["satellite"], "S1B")


class Forecast(unittest.TestCase):
    def test_predicted_peak_median(self):
        d = days("2020-07-01", 4)
        m = [[1, 5, 3, 1], [1, 2, 9, 1], [1, 6, 4, None]]
        self.assertEqual(hindcast.predicted_peak(d, m), "2020-07-02")   # median 5 on day 2 vs 4 on day 3

    def test_cloud_lookup(self):
        tau = T("2020-07-01T00:00:00")
        look = hindcast.cloud_lookup_factory(tau, [(tau, 0.0), (tau + timedelta(hours=6), 60.0)])
        self.assertAlmostEqual(look(tau + timedelta(hours=3)), 30.0)
        self.assertIsNone(look(tau + timedelta(days=16)))

    def test_forecast_uses_predictor(self):
        tau = T("2020-07-01T00:00:00")
        passes = [{"satellite": "S2A", "time": T("2020-07-05T04:00:00"), "kind": "optical", "mode": None, "source": "planned"},
                  {"satellite": "S1A", "time": T("2020-07-07T12:00:00"), "kind": "sar", "mode": None, "source": "planned"}]
        cloud = [(tau, 90.0), (tau + timedelta(days=15), 90.0)]
        f = hindcast.forecast(tau, "2020-07-04", passes, {"S2A": T("2020-07-20T00:00:00"), "S1A": T("2020-07-20T00:00:00")}, cloud)
        self.assertEqual(f["naive_time"], T("2020-07-05T04:00:00"))
        self.assertEqual(f["t_hat"], T("2020-07-07T12:00:00"))     # cloudy S2 skipped

    def test_baselines(self):
        past = [{"satellite": "S1A", "time": T("2020-06-11T12:00:00")}]
        self.assertEqual(baselines.next_s1_projection("2020-07-04", past, T("2020-07-01T00:00:00")),
                         T("2020-07-05T12:00:00"))
        site = [(date(2019, 7, 1), 100.0), (date(2018, 7, 4), 50.0), (date(2020, 7, 1), 1.0), (date(2019, 8, 1), 9.0)]
        self.assertEqual(baselines.climatology("2020-07-04", site, 2020, 7), T("2020-07-05T00:00:00") + timedelta(hours=75))


class Scoring(unittest.TestCase):
    def test_holm(self):
        self.assertEqual(list(scoring.holm([0.01, 0.04, 0.03])), [0.03, 0.06, 0.06])

    def test_delta_mae_and_verdict(self):
        eb = [100.0] * 40
        ew = [10.0] * 40
        r = scoring.delta_mae(eb, ew, list(range(20)) * 2, n_boot=200)
        self.assertEqual(r["delta_mae_h"], 90.0)
        self.assertEqual(scoring.verdict(r, 0.001), "beats baseline by a useful margin")
        self.assertEqual(scoring.verdict({"delta_mae_h": 1.0, "ci95": (-3.0, 5.0)}, 0.5), "no useful gain")

    def test_kaplan_meier(self):
        t, s = scoring.kaplan_meier([10, 20, 20, 720], [False, False, False, True])
        self.assertEqual(t, [10.0, 20.0])
        self.assertAlmostEqual(s[-1], 0.25)


class Guard(unittest.TestCase):
    def test_guard(self):
        self.assertFalse(guard.plan_approved("Status: **DRAFT, not yet approved.**"))
        self.assertTrue(guard.plan_approved("Status: **approved by Janice on 1 Dec 2026**"))
        self.assertEqual(guard.require_outcome_access(["P01", "P02"]), "pilot")
        with self.assertRaises(guard.PlanNotApproved):
            guard.require_outcome_access(["P01", "E0001"], plan_text="Status: **DRAFT**")
        self.assertEqual(guard.require_outcome_access(["E0001"], plan_text="Status: **approved by Janice on 1 Dec 2026**"),
                         "main")
        self.assertFalse(guard.plan_approved())     # the committed plan is still a draft


if __name__ == "__main__":
    unittest.main()
