"""Physical rotations and propagation independence, using synthetic measurements."""

import unittest
import numpy as np
import pandas as pd

from imu_thesis.data import GYRO
from imu_thesis.orientation import (error_rotation_vector, from_rotation_vector,
                                    integrate_at_epochs, multiply,
                                    orientation_diagnostic, reference_quaternion)


EPOCH = 1621218775000000000


def rotate(q, vector):
    return multiply(multiply(q, np.r_[0, vector]), q*[1, -1, -1, -1])[1:]


class OrientationTests(unittest.TestCase):
    def test_reference_cardinal_directions_and_tilts(self):
        # North-facing vehicle's right/forward/up = East/North/Up.
        np.testing.assert_allclose(reference_quaternion(0, 0, 0), [1, 0, 0, 0])
        np.testing.assert_allclose(rotate(reference_quaternion(0, 0, 90), [0, 1, 0]), [1, 0, 0], atol=1e-14)
        np.testing.assert_allclose(rotate(reference_quaternion(90, 0, 0), [1, 0, 0]), [0, 0, -1], atol=1e-14)
        np.testing.assert_allclose(rotate(reference_quaternion(0, 90, 0), [0, 1, 0]), [0, 0, 1], atol=1e-14)

    def test_noncommuting_body_rotations_use_right_multiplication(self):
        x = from_rotation_vector([np.pi/2, 0, 0])
        y = from_rotation_vector([0, np.pi/2, 0])
        np.testing.assert_allclose(rotate(multiply(x, y), [1, 0, 0]), [0, 1, 0], atol=1e-14)
        np.testing.assert_allclose(rotate(multiply(y, x), [1, 0, 0]), [0, 0, -1], atol=1e-14)

    def test_constant_body_rate_from_nonidentity_initial_with_split_boundaries(self):
        times = EPOCH+np.arange(101, dtype=np.int64)*10_000_000
        epochs = EPOCH+np.array([5_000_001, 325_000_001, 995_000_001], dtype=np.int64)
        omega = np.array([.3, -.2, .5])
        q0 = reference_quaternion(10, 20, 80)
        result, _ = integrate_at_epochs(times, np.tile(omega, (len(times), 1)), epochs, q0)
        for time, q in zip(epochs, result):
            elapsed = int(time-epochs[0])/1e9
            expected = multiply(q0, from_rotation_vector(omega*elapsed))
            np.testing.assert_allclose(error_rotation_vector(expected, q), 0, atol=1e-13)
        np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1, atol=1e-14)

    def test_sign_equivalence_and_zero_rotation(self):
        q = reference_quaternion(5, -3, 359)
        np.testing.assert_allclose(error_rotation_vector(q, -q), 0, atol=1e-14)
        np.testing.assert_array_equal(from_rotation_vector([0, 0, 0]), [1, 0, 0, 0])

    def test_reference_after_initialization_cannot_reset_estimate(self):
        times = EPOCH+np.arange(201, dtype=np.int64)*10_000_000
        imu = pd.DataFrame({"time_ns": times, **{col: np.full(len(times), .1 if k==2 else 0.) for k,col in enumerate(GYRO)}})
        ref = pd.DataFrame({"time_ns": EPOCH+np.arange(3, dtype=np.int64)*1_000_000_000,
                            "roll_deg": 0., "pitch_deg": 0., "heading_deg": [0., -5., -10.], "quality_code": 2.})
        first, _ = orientation_diagnostic(imu, ref)
        ref.loc[1:, "heading_deg"] = [100., 170.]
        second, _ = orientation_diagnostic(imu, ref)
        columns = [f"estimated_q_{a}" for a in "wxyz"]
        np.testing.assert_array_equal(first[columns], second[columns])
        self.assertNotEqual(first.angle_difference_deg.iloc[-1], second.angle_difference_deg.iloc[-1])

    def test_gap_rejection_and_no_extrapolation(self):
        times = EPOCH+np.array([0, 10_000_000, 1_000_000_000], dtype=np.int64)
        gyro = np.zeros((3, 3))
        with self.assertRaises(ValueError):
            integrate_at_epochs(times, gyro, times[[0, -1]], [1, 0, 0, 0])
        with self.assertRaises(ValueError):
            integrate_at_epochs(times, gyro, [EPOCH-1, EPOCH+1], [1, 0, 0, 0])
        with self.assertRaises(ValueError):
            integrate_at_epochs(times[::-1], gyro, times[[0, -1]], [1, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
