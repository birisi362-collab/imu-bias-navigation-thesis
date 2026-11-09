import unittest

import numpy as np
import pandas as pd

from imu_thesis.data import ACCEL, GYRO
from imu_thesis.earth_rate import EARTH_RATE_RAD_S, earth_rate_comparison, earth_rate_enu
from imu_thesis.orientation import (error_rotation_vector, from_rotation_vector,
                                    integrate_at_epochs, multiply, reference_quaternion)

EPOCH = 1621218775000000000


def rotate(q, vector):
    return multiply(multiply(q, np.r_[0., vector]), q * [1, -1, -1, -1])[1:]


class EarthRateTests(unittest.TestCase):
    def test_enu_projection_at_equator_poles_and_invalid_latitude(self):
        for lat, expected in [(0, [0, 1, 0]), (90, [0, 0, 1]), (-90, [0, 0, -1])]:
            np.testing.assert_allclose(earth_rate_enu(lat), EARTH_RATE_RAD_S*np.array(expected), atol=1e-19)
        for lat in [91, -91, np.nan, np.inf]:
            with self.assertRaises(ValueError):
                earth_rate_enu(lat)

    def test_stationary_earth_fixed_body_at_nontrivial_attitude(self):
        times = EPOCH + np.arange(6001, dtype=np.int64)*10_000_000
        epochs = times[::100]
        q0 = reference_quaternion(12, -8, 130)
        earth = earth_rate_enu(22.3)
        gyro = np.tile(rotate(q0*[1, -1, -1, -1], earth), (len(times), 1))
        result, _ = integrate_at_epochs(times, gyro, epochs, q0, navigation_rate_enu_rad_s=earth)
        for q in result:
            np.testing.assert_allclose(error_rotation_vector(q0, q), 0, atol=1e-12)
        raw, _ = integrate_at_epochs(times, gyro, epochs, q0)
        self.assertAlmostEqual(np.linalg.norm(error_rotation_vector(q0, raw[-1])), EARTH_RATE_RAD_S*60, places=11)

    def test_noncommuting_constant_left_and_right_rates(self):
        times = EPOCH + np.arange(101, dtype=np.int64)*10_000_000
        q0 = reference_quaternion(10, 20, 80)
        body, navigation = np.array([.3, -.2, .5]), np.array([.1, .4, -.2])
        result, _ = integrate_at_epochs(times, np.tile(body, (101, 1)), times[::10], q0,
                                         navigation_rate_enu_rad_s=navigation)
        expected = multiply(multiply(from_rotation_vector(-navigation), q0), from_rotation_vector(body))
        np.testing.assert_allclose(error_rotation_vector(expected, result[-1]), 0, atol=1e-13)

    def test_turn_after_calibration_no_double_subtraction_or_future_reference(self):
        seconds = np.arange(1001)*.01
        times = EPOCH + np.arange(1001, dtype=np.int64)*10_000_000
        earth = earth_rate_enu(22.3)
        bias = np.array([.001, -.002, .003])
        # Smooth yaw rate after calibration, with no rate discontinuity at t=5.
        yaw = .1*np.maximum(seconds-5, 0)**2
        rates = []
        for t, angle in zip(seconds, yaw):
            q = from_rotation_vector([0, 0, angle])
            rates.append(rotate(q*[1, -1, -1, -1], earth) + bias + [0, 0, .2*max(t-5, 0)])
        imu = pd.DataFrame({"time_ns": times})
        for i, col in enumerate(GYRO):
            imu[col] = np.array(rates)[:, i]
        for i, col in enumerate(ACCEL):
            imu[col] = 9.81 if i == 2 else 0.
        ref = pd.DataFrame({"time_ns": times[::100], "roll_deg": 0., "pitch_deg": 0.,
                            "heading_deg": -np.rad2deg(yaw[::100]), "latitude_deg": 22.3,
                            "quality_code": 2.})
        for axis in "xyz":
            ref[f"velocity_body_{axis}_m_s"] = 0.
        table, report = earth_rate_comparison(imu, ref, 5., 5.)
        np.testing.assert_allclose(report["earth_separated_initial_offset_rad_s"], bias, atol=1e-15)
        self.assertLess(table.fixed_earth_angle_difference_deg.iloc[-1], 1e-6)
        self.assertGreater(table.fixed_angle_difference_deg.iloc[-1], .005)
        ref.loc[ref.time_ns > EPOCH+5_000_000_000, ["heading_deg", "latitude_deg"]] = [170, -80]
        changed, changed_report = earth_rate_comparison(imu, ref, 5., 5.)
        self.assertEqual(report["latitude_deg"], changed_report["latitude_deg"])
        for variant in report["variants"]:
            cols = [f"{variant}_estimated_q_{a}" for a in "wxyz"]
            np.testing.assert_array_equal(table[cols], changed[cols])


if __name__ == "__main__":
    unittest.main()
