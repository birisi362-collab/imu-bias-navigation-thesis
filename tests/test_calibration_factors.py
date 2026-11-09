import unittest

import numpy as np

from imu_thesis.calibration_factors import compare_calibration_factors
from imu_thesis.data import GYRO
from imu_thesis.earth_rate import earth_rate_enu
from test_post_stop import EPOCH, fixture as base_fixture


def fixture():
    imu, ref, old, recent = base_fixture()
    seconds = (imu.time_ns.to_numpy()-EPOCH)/1e9
    for i, col in enumerate(GYRO):
        imu[col] = np.where(seconds < 26, old[i], recent[i])+earth_rate_enu(22.)[i]
    ref["velocity_body_y_m_s"] = 2.
    ref.loc[(ref.index<=25)|ref.index.to_series().between(60,85)|
            ref.index.to_series().between(100,125), "velocity_body_y_m_s"] = 0.
    return imu, ref, old, recent


class CalibrationFactorTests(unittest.TestCase):
    def test_same_lengths_fixed_old_baseline_and_disjoint_future_intervals(self):
        imu, ref, old, recent = fixture()
        table, report = compare_calibration_factors(imu, ref, 10.)
        self.assertEqual(report["baseline_stop_id"], 1)
        self.assertEqual([e["stop_id"] for e in report["experiments"]], [2,3])
        for e in report["experiments"]:
            self.assertEqual(e["status"], "evaluated")
            for name,w in e["calibrations"].items():
                self.assertEqual(w["duration_s"], 5. if name.endswith("short") else 20.)
                self.assertLess(w["end_time_ns_exclusive"],e["evaluation"]["start_time_ns"])
                expected = old if name.startswith("old") else recent
                np.testing.assert_allclose(e["evaluation"]["variants"][name]["gyro_offset_subtracted_xyz_rad_s"], expected, atol=1e-15)
            self.assertEqual(e["calibrations"]["old_long"], report["baseline_calibrations"]["long"])
        self.assertLess(table.recent_long_angle_difference_deg.max(),1e-8)
        self.assertLess(table.recent_short_angle_difference_deg.max(),1e-8)
        self.assertGreater(table.old_long_angle_difference_deg.iloc[-1],.5)

    def test_future_reference_cannot_change_predictions_or_fitted_offsets(self):
        imu, ref, _, _ = fixture()
        first, report = compare_calibration_factors(imu, ref, 10.)
        ref.loc[ref.index>=127,"heading_deg"] = 80.
        second, changed = compare_calibration_factors(imu, ref, 10.)
        self.assertEqual(report["baseline_calibrations"], changed["baseline_calibrations"])
        for a,b in zip(report["experiments"],changed["experiments"]):
            self.assertEqual(a["calibrations"],b["calibrations"])
        for name in ["old_short","old_long","recent_short","recent_long"]:
            cols = [f"{name}_estimated_q_{a}" for a in "wxyz"]
            np.testing.assert_array_equal(first[cols],second[cols])
        self.assertGreater(second.recent_long_angle_difference_deg.iloc[-1],70.)

    def test_no_later_stop_is_not_counted_as_age_evidence(self):
        imu, ref, _, _ = fixture()
        ref.loc[ref.index>=26,"velocity_body_y_m_s"] = 2.
        table,r = compare_calibration_factors(imu,ref,10.)
        self.assertTrue(table.empty)
        self.assertEqual(r["experiments"],[])
        for kwargs in [{"short_s":20.},{"short_s":0.},{"long_s":np.nan}]:
            with self.assertRaises(ValueError):
                compare_calibration_factors(imu,ref,**kwargs)


if __name__ == "__main__":
    unittest.main()
