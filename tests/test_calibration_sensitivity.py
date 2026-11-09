import unittest

import numpy as np

from imu_thesis.calibration_sensitivity import compare_calibration_lengths
from test_initial_correction import EPOCH, stationary_fixture


class CalibrationLengthTests(unittest.TestCase):
    def test_known_offset_same_evaluation_after_longest_window(self):
        imu, ref, offset = stationary_fixture()
        table, report = compare_calibration_lengths(imu, ref, (3., 4.), 1.)
        self.assertEqual(report["evaluation_start_time_ns"], EPOCH+4_000_000_000)
        for name, item in report["variants"].items():
            np.testing.assert_allclose(item["calibration"]["gyro_offset_xyz_rad_s"], offset, atol=1e-15)
            np.testing.assert_allclose(table[f"{name}_angle_difference_deg"], 0, atol=1e-10)
            for a in "wxyz":
                self.assertEqual(table[f"{name}_estimated_q_{a}"].iloc[0], table[f"raw_estimated_q_{a}"].iloc[0])

    def test_rejected_longest_window_cannot_move_evaluation_start(self):
        imu, ref, _ = stationary_fixture()
        ref.loc[ref.time_ns == EPOCH+3_000_000_000, "velocity_body_y_m_s"] = 1.
        table, report = compare_calibration_lengths(imu, ref, (3., 4.), 1.)
        self.assertEqual(report["variants"]["cal_0"]["status"], "accepted_candidate")
        self.assertEqual(report["variants"]["cal_1"]["status"], "rejected")
        self.assertNotIn("cal_1_angle_difference_deg", table)
        self.assertEqual(int(table.time_ns.iloc[0]), EPOCH+4_000_000_000)

    def test_future_reference_changes_scores_but_not_estimates_or_offsets(self):
        imu, ref, _ = stationary_fixture()
        first, report = compare_calibration_lengths(imu, ref, (3., 4.), 1.)
        ref.loc[ref.time_ns > EPOCH+4_000_000_000, "heading_deg"] = 100.
        second, changed = compare_calibration_lengths(imu, ref, (3., 4.), 1.)
        for name in report["variants"]:
            self.assertEqual(report["variants"][name]["calibration"], changed["variants"][name]["calibration"])
            cols = [f"{name}_estimated_q_{a}" for a in "wxyz"]
            np.testing.assert_array_equal(first[cols], second[cols])
        self.assertNotEqual(first.cal_0_angle_difference_deg.iloc[-1], second.cal_0_angle_difference_deg.iloc[-1])

    def test_invalid_lengths_rejected(self):
        imu, ref, _ = stationary_fixture()
        for lengths in [(), (0.,), (-1.,), (np.nan,), (2., 2.), [[2.]]]:
            with self.assertRaises(ValueError):
                compare_calibration_lengths(imu, ref, lengths)


if __name__ == "__main__":
    unittest.main()
