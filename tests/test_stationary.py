import unittest

import numpy as np
import pandas as pd

from imu_thesis.data import ACCEL, GYRO
from imu_thesis.earth_rate import earth_rate_enu
from imu_thesis.stationary import analyze_stops

EPOCH = 1621218775000000000


def fixture():
    times = EPOCH+np.arange(6001, dtype=np.int64)*10_000_000
    bias = np.array([.001, -.002, .003])
    imu = pd.DataFrame({"time_ns": times})
    for i, col in enumerate(GYRO):
        imu[col] = bias[i]+earth_rate_enu(22.)[i]
    for i, col in enumerate(ACCEL):
        imu[col] = 9.81 if i==2 else 0.
    ref = pd.DataFrame({"time_ns": times[::100], "roll_deg": 0., "pitch_deg": 0.,
                        "heading_deg": 0., "latitude_deg": 22., "quality_code": 2.})
    for axis in "xyz":
        ref[f"velocity_body_{axis}_m_s"] = 0.
    ref.loc[ref.index.isin(range(26, 30)), "velocity_body_y_m_s"] = 2.
    return imu, ref, bias


class StationaryTests(unittest.TestCase):
    def test_equal_windows_separate_stops_and_remove_earth_once(self):
        imu, ref, bias = fixture()
        _, r = analyze_stops(imu, ref)
        self.assertEqual(r["candidate_count"], 2)
        self.assertEqual([w["start_s"] for w in r["equal_windows"]], [1., 31.])
        for w in r["equal_windows"]:
            self.assertEqual(w["imu_samples"], 2000)
            for i, axis in enumerate("xyz"):
                self.assertAlmostEqual(w[f"offset_candidate_{axis}_rad_s"], bias[i], places=13)
                self.assertAlmostEqual(w[f"second_minus_first_{axis}_rad_s"], 0., places=13)

    def test_rotation_and_missing_imu_reject_candidates(self):
        imu, ref, _ = fixture()
        ref.loc[ref.index==10, "heading_deg"] = 1.
        imu = imu.loc[~imu.index.isin(range(4000, 4050))]
        _, r = analyze_stops(imu, ref)
        self.assertEqual(r["candidate_count"], 0)
        self.assertEqual(len(r["equal_windows"]), 0)
        self.assertTrue(all(x["status"]=="rejected" for x in r["inventory"]))

    def test_reference_gaps_are_not_bridged(self):
        imu, ref, _ = fixture()
        ref = ref.loc[~ref.index.isin(range(10, 20))]
        _, r = analyze_stops(imu, ref)
        self.assertEqual([w["start_s"] for w in r["equal_windows"]], [31.])
        self.assertEqual(r["candidate_count"], 3)

    def test_future_outside_window_does_not_change_window_statistics(self):
        imu, ref, _ = fixture()
        _, first = analyze_stops(imu, ref)
        imu.loc[imu.time_ns>=EPOCH+51_000_000_000, GYRO] = 10.
        _, second = analyze_stops(imu, ref)
        self.assertEqual(first["equal_windows"], second["equal_windows"])

    def test_bad_timestamps_and_parameters_rejected(self):
        imu, ref, _ = fixture()
        with self.assertRaises(ValueError):
            analyze_stops(imu.iloc[::-1], ref)
        for kwargs in [{"window_s": 0}, {"edge_s": -1}, {"speed_limit_m_s": np.nan}]:
            with self.assertRaises(ValueError):
                analyze_stops(imu, ref, **kwargs)


if __name__ == "__main__":
    unittest.main()
