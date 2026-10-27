import unittest

import numpy as np
import pandas as pd

from imu_thesis.data import ACCEL, GYRO
from imu_thesis.initial_correction import compare_initial_correction, estimate_initial_offset


EPOCH = 1621218775000000000


def stationary_fixture():
    times = EPOCH+np.arange(501, dtype=np.int64)*10_000_000
    offset = np.array([.001, -.002, .003])
    imu = pd.DataFrame({"time_ns": times})
    for k, column in enumerate(GYRO):
        imu[column] = offset[k]
    for k, column in enumerate(ACCEL):
        imu[column] = 9.81 if k==2 else 0.
    ref = pd.DataFrame({"time_ns": EPOCH+np.arange(6, dtype=np.int64)*1_000_000_000,
                        "roll_deg": 0., "pitch_deg": 0., "heading_deg": 0., "quality_code": 2.})
    for axis in "xyz":
        ref[f"velocity_body_{axis}_m_s"] = 0.
    return imu, ref, offset


class InitialCorrectionTests(unittest.TestCase):
    def test_known_constant_offset_removed_on_disjoint_evaluation(self):
        imu, ref, offset = stationary_fixture()
        table, report = compare_initial_correction(imu, ref, 3., 2.)
        np.testing.assert_allclose(report["calibration"]["gyro_offset_xyz_rad_s"], offset, atol=1e-15)
        self.assertEqual(report["calibration"]["imu_samples"], 300)
        self.assertEqual(int(table.time_ns.iloc[0]), EPOCH+3_000_000_000)
        np.testing.assert_allclose(table.fixed_angle_difference_deg, 0, atol=1e-10)
        self.assertGreater(table.raw_angle_difference_deg.iloc[-1], .4)
        for axis in "wxyz":
            self.assertEqual(table[f"raw_estimated_q_{axis}"].iloc[0], table[f"fixed_estimated_q_{axis}"].iloc[0])

    def test_future_measurements_cannot_change_initial_offset(self):
        imu, ref, _ = stationary_fixture()
        first, _ = estimate_initial_offset(imu, ref, 3.)
        imu.loc[imu.time_ns >= EPOCH+3_000_000_000, GYRO] = 10.
        ref.loc[ref.time_ns >= EPOCH+3_000_000_000, ["heading_deg", "velocity_body_y_m_s"]] = [120., 20.]
        second, _ = estimate_initial_offset(imu, ref, 3.)
        np.testing.assert_array_equal(first, second)

    def test_moving_or_rotating_calibration_is_rejected(self):
        for column, value in [("velocity_body_y_m_s", 1.), ("heading_deg", 2.)]:
            imu, ref, _ = stationary_fixture()
            ref.loc[1, column] = value
            with self.assertRaises(ValueError):
                estimate_initial_offset(imu, ref, 3.)

    def test_missing_reference_or_imu_gap_is_rejected(self):
        imu, ref, _ = stationary_fixture()
        with self.assertRaises(ValueError):
            estimate_initial_offset(imu, ref.iloc[[0, 3, 4, 5]], 3.)
        imu = imu.loc[~imu.index.isin(range(100, 120))]
        with self.assertRaises(ValueError):
            estimate_initial_offset(imu, ref, 3.)


if __name__ == "__main__":
    unittest.main()
