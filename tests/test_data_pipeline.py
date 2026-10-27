"""Small synthetic fixtures check parsing and timing; they are NOT UrbanNav data."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from imu_thesis.audit import audit_data
from imu_thesis.data import ACCEL, GYRO, dms_to_degrees, read_imu, read_reference, relative_seconds, seconds_to_ns


EPOCH = 1621218775000000000


def frames(times, ref_times):
    imu = pd.DataFrame({"time_ns": np.array(times, dtype=np.int64)})
    for column in GYRO + ACCEL:
        imu[column] = 0.
    ref = pd.DataFrame({"time_ns": np.array(ref_times, dtype=np.int64), "quality_code": 2., "heading_deg": 0.})
    return imu, ref


class TimingTests(unittest.TestCase):
    def test_nanosecond_precision_is_preserved(self):
        self.assertEqual(seconds_to_ns("1621218775.000000001"), EPOCH + 1)
        np.testing.assert_array_equal(relative_seconds([EPOCH, EPOCH + 1], EPOCH), [0, 1e-9])

    def test_coordinates_include_negative_zero_hemisphere(self):
        self.assertAlmostEqual(dms_to_degrees("-0", "30", "0", 90), -.5)
        with self.assertRaises(ValueError):
            dms_to_degrees("22", "61", "0", 90)

    def test_nearest_pairing_and_overlap_do_not_extrapolate(self):
        imu, ref = frames([EPOCH, EPOCH + 10_000_000, EPOCH + 20_000_000],
                          [EPOCH - 1, EPOCH + 9_000_000, EPOCH + 20_000_001])
        report, paired = audit_data(imu, ref, .002)
        self.assertFalse(report["errors"])
        self.assertEqual(len(paired), 1)
        self.assertEqual(paired.nearest_imu_time_ns.iloc[0], EPOCH + 10_000_000)
        self.assertAlmostEqual(paired.time_offset_ms.iloc[0], 1.)
        self.assertEqual(report["time_matching"]["reference_epochs_outside_overlap"], 2)

    def test_gap_is_not_filled_with_fake_imu(self):
        imu, ref = frames([EPOCH, EPOCH + 2_500_000, EPOCH + 5_000_000, EPOCH + 2_000_000_000],
                          [EPOCH, EPOCH + 1_000_000_000, EPOCH + 2_000_000_000])
        report, paired = audit_data(imu, ref)
        self.assertEqual(report["imu"]["gaps_over_3x_median"], 1)
        self.assertEqual(report["time_matching"]["unmatched"], 1)
        self.assertTrue(pd.isna(paired.nearest_imu_time_ns.iloc[1]))
        self.assertTrue(pd.isna(paired.gyro_x_rad_s.iloc[1]))

    def test_bad_order_is_reported_not_silently_sorted(self):
        for times in [[EPOCH, EPOCH], [EPOCH + 10, EPOCH]]:
            imu, ref = frames(times, [EPOCH, EPOCH + 20])
            report, paired = audit_data(imu, ref)
            self.assertTrue(report["errors"])
            self.assertTrue(paired.empty)

    def test_no_overlap_is_an_error(self):
        imu, ref = frames([EPOCH, EPOCH + 10], [EPOCH + 100, EPOCH + 200])
        report, _ = audit_data(imu, ref)
        self.assertTrue(report["errors"])

    def test_nonfinite_sensor_value_is_an_error(self):
        imu, ref = frames([EPOCH, EPOCH + 1_000_000_000], [EPOCH, EPOCH + 1_000_000_000])
        imu.loc[0, GYRO[0]] = np.nan
        report, _ = audit_data(imu, ref)
        self.assertTrue(report["errors"])


class ReaderTests(unittest.TestCase):
    def test_imu_uses_sensor_stamp_and_ignores_ahrs_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "imu.csv"
            data = {"%time": [EPOCH + 1000, EPOCH + 2000], "field.header.stamp": [EPOCH + 1, EPOCH + 2], "field.orientation.w": [1, 1]}
            for kind in ["angular_velocity", "linear_acceleration"]:
                for axis in "xyz":
                    data[f"field.{kind}.{axis}"] = [0., 0.]
            pd.DataFrame(data).to_csv(path, index=False)
            frame = read_imu(path)
            self.assertEqual(frame.time_ns.iloc[0], EPOCH + 1)
            self.assertEqual(list(frame.columns), ["time_ns", *GYRO, *ACCEL])

    def test_reference_dms_units_and_utc_not_gps_time(self):
        text = ("UTCTime Week GPSTime Latitude Longitude H-Ell VelBdyX VelBdyY VelBdyZ AccBdyX AccBdyY AccBdyZ Roll Pitch Heading Q\n"
                "(sec) (weeks) (sec) (+/-D M S) (+/-D M S) (m) (m/s) (m/s) (m/s) (m/s^2) (m/s^2) (m/s^2) (deg) (deg) (deg)\n"
                "1621218775.00 2158 95593 22 18 4.32 114 10 44.6 3.47 0 0 0 0 0 0 -1.7 .4 -132.5 2\n"
                "1621218776.00 2158 95594 22 18 4.32 114 10 44.6 3.47 0 0 0 0 0 0 -1.7 .4 -132.5 2\n")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.txt"
            path.write_text(text)
            frame = read_reference(path, "0.000000001")
            self.assertEqual(frame.time_ns.iloc[0], EPOCH + 1)
            self.assertAlmostEqual(frame.latitude_deg.iloc[0], 22.3012)
            self.assertAlmostEqual(frame.heading_deg.iloc[0], -132.5)
            path.write_text(text + "bad row\n")
            with self.assertRaises(ValueError):
                read_reference(path)


if __name__ == "__main__":
    unittest.main()
