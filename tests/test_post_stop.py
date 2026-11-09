import unittest

import numpy as np
import pandas as pd

from imu_thesis.data import ACCEL, GYRO
from imu_thesis.earth_rate import earth_rate_enu
from imu_thesis.post_stop import compare_interval, compare_post_stop

EPOCH = 1621218775000000000


def fixture():
    seconds = np.arange(15001)*.01
    imu = pd.DataFrame({"time_ns": EPOCH+np.arange(len(seconds), dtype=np.int64)*10_000_000})
    old, recent = np.array([.001, -.001, .002]), np.array([.002, -.002, .003])
    earth = earth_rate_enu(22.)
    for i, col in enumerate(GYRO):
        imu[col] = np.where(seconds < 6, old[i], recent[i])+earth[i]
    for i, col in enumerate(ACCEL):
        imu[col] = 9.81 if i==2 else 0.
    ref = pd.DataFrame({"time_ns": imu.time_ns.to_numpy()[::100], "roll_deg": 0.,
                        "pitch_deg": 0., "heading_deg": 0., "latitude_deg": 22., "quality_code": 2.})
    for axis in "xyz":
        ref[f"velocity_body_{axis}_m_s"] = 0.
    # Straight travel with a short initial stop and one long later stop.
    ref.loc[(ref.index>=6)&((ref.index<30)|(ref.index>55)), "velocity_body_y_m_s"] = 2.
    return imu, ref, old, recent


class PostStopTests(unittest.TestCase):
    def test_known_changed_offset_improves_future_interval_without_overlap(self):
        imu, ref, old, recent = fixture()
        table, report = compare_post_stop(imu, ref, duration_s=10.)
        evaluated = [e for e in report["experiments"] if e["status"]=="evaluated"]
        self.assertEqual(len(evaluated), 1)
        e = evaluated[0]
        self.assertEqual(e["evaluation"]["start_time_ns"], EPOCH+56_000_000_000)
        self.assertLess(e["calibration_window"]["end_time_ns_exclusive"], e["evaluation"]["start_time_ns"])
        np.testing.assert_allclose(report["initial_calibration"]["earth_separated_offset_xyz_rad_s"], old, atol=1e-15)
        np.testing.assert_allclose(e["evaluation"]["variants"]["recent"]["gyro_offset_subtracted_xyz_rad_s"], recent, atol=1e-15)
        self.assertLess(table.recent_angle_difference_deg.max(), 1e-8)
        self.assertGreater(table.initial_angle_difference_deg.iloc[-1], .5)
        for name in ["no_offset", "initial", "recent"]:
            self.assertAlmostEqual(table[f"{name}_angle_difference_deg"].iloc[0], 0.)

    def test_future_reference_changes_scores_not_predictions_or_offsets(self):
        imu, ref, _, _ = fixture()
        first, report = compare_post_stop(imu, ref, 10.)
        ref.loc[ref.index>=57, "heading_deg"] = 80.
        second, changed = compare_post_stop(imu, ref, 10.)
        self.assertEqual(report["initial_calibration"], changed["initial_calibration"])
        self.assertEqual(report["experiments"][0]["calibration_window"], changed["experiments"][0]["calibration_window"])
        for name in ["no_offset", "initial", "recent"]:
            cols = [f"{name}_estimated_q_{a}" for a in "wxyz"]
            np.testing.assert_array_equal(first[cols], second[cols])
        self.assertGreater(second.recent_angle_difference_deg.iloc[-1], 70.)

    def test_future_imu_cannot_change_fitted_offset(self):
        imu, ref, _, _ = fixture()
        _, before = compare_post_stop(imu, ref, 10.)
        imu.loc[imu.time_ns>=EPOCH+56_000_000_000, GYRO] = .1
        _, after = compare_post_stop(imu, ref, 10.)
        self.assertEqual(before["experiments"][0]["calibration_window"], after["experiments"][0]["calibration_window"])
        self.assertEqual(before["initial_calibration"], after["initial_calibration"])

    def test_partial_duration_and_reference_gap_rejected(self):
        imu, ref, _, _ = fixture()
        with self.assertRaises(ValueError):
            compare_interval(imu, ref, {"raw": [0, 0, 0]}, EPOCH+145_000_000_000, 10.)
        missing = ref.loc[ref.index!=60]
        with self.assertRaises(ValueError):
            compare_interval(imu, missing, {"raw": [0, 0, 0]}, EPOCH+56_000_000_000, 10.)
        table, report = compare_post_stop(imu, ref, 120.)
        self.assertTrue(table.empty)
        self.assertEqual(report["experiments"][0]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
