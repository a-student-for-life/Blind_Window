"""Offline test of the pilot driver's bookkeeping, RQ2 matching and report, with hand-made stage files."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from study import pilot


class PilotDriver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.p = mock.patch.object(pilot, "OUT", self.out)
        self.p.start()
        pilot.save("P01", "glofas", {"cell": [26.175, 91.725], "event": {
            "peak_date": "2024-07-01", "t0": "2024-07-02T00:00:00+00:00",
            "onset": "2024-06-28T00:00:00+00:00", "end": "2024-07-06T00:00:00+00:00"}})
        pilot.save("P01", "observed", {"bw_any_h": 227.95, "bw_s1_h": 227.95, "bw_s2_h": 720, "missed": True,
                                        "first_usable_time": "2024-07-11T11:57:00+00:00", "acquisitions": [
            {"time": "2024-07-04T04:41:00+00:00", "satellite": "S2A", "mission": "S2", "usable": False},
            {"time": "2024-07-11T11:57:00+00:00", "satellite": "S1A", "mission": "S1", "usable": True}]})
        pilot.save("P01", "asf", {"passes": [{"satellite": "S1A", "time": "2024-07-11T11:57:03+00:00"},
                                             {"satellite": "S1A", "time": "2024-06-29T11:57:03+00:00"}]})
        pilot.save("P01", "plans", {"plans": [
            {"satellite": "S1A", "issued": "2024-06-20T00:00:00+00:00", "valid_to": "2024-07-20T00:00:00+00:00",
             "passes": [{"satellite": "S1A", "time": "2024-07-11T11:57:00+00:00", "kind": "sar"}]},
            {"satellite": "S2A", "issued": "2024-06-20T00:00:00+00:00", "valid_to": "2024-07-20T00:00:00+00:00",
             "passes": [{"satellite": "S2A", "time": "2024-07-04T04:41:00+00:00", "kind": "optical"}]}]})

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_rq2(self):
        r = pilot.rq2({"id": "P01"})
        self.assertEqual(r["S1"]["n_actual"], 2)        # 29 Jun and 11 Jul
        self.assertEqual(r["S1"]["n_matched"], 1)       # 29 Jun was not planned
        self.assertEqual(r["S1"]["recall"], 0.5)
        self.assertEqual(r["S2"]["precision"], 1.0)

    def test_planned_as_of(self):
        passes, ends = pilot.planned_as_of(pilot.load("P01", "plans")["plans"], pilot._dt("2024-06-29T00:00:00+00:00"))
        self.assertEqual({p["satellite"] for p in passes}, {"S1A", "S2A"})
        self.assertIn("S1A", ends)

    def test_skip_done_and_report(self):
        calls = []
        fake = {s: (lambda ev, s=s: calls.append(s) or {"x": 1}) for s in pilot.STAGES}
        with mock.patch.object(pilot, "RUNNERS", fake), \
             mock.patch.object(pilot, "pilots", lambda: [{"id": "P01", "name": "Guwahati"}]):
            pilot.run()
            self.assertNotIn("glofas", calls)           # already saved: skipped
            self.assertIn("floodplain", calls)
            text = (self.out / "PILOT_SUMMARY.md").read_text()
            self.assertIn("227.95", text)
            self.assertIn("0.50", text)


if __name__ == "__main__":
    unittest.main()
