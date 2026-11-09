"""Fixed-latitude Earth-rate ablation; not moving local-level mechanization."""

import numpy as np

from .data import GYRO
from .initial_correction import estimate_initial_offset
from .orientation import multiply, orientation_diagnostic, reference_quaternion

EARTH_RATE_RAD_S = 7.292115e-5  # WGS 84 nominal angular velocity, NGA.


def earth_rate_enu(latitude_deg):
    if not np.isfinite(latitude_deg) or not -90 <= latitude_deg <= 90:
        raise ValueError("Enlem -90 ile 90 derece arasında ve sonlu olmalı.")
    latitude = np.deg2rad(latitude_deg)
    return EARTH_RATE_RAD_S * np.array([0., np.cos(latitude), np.sin(latitude)])


def earth_rate_comparison(imu, reference, calibration_duration_s=5., duration_s=60., max_gap_s=.02):
    mean, calibration = estimate_initial_offset(imu, reference, calibration_duration_s, max_gap_s)
    cal_ref = reference.loc[(reference.time_ns >= calibration["start_time_ns"]) &
                            (reference.time_ns < calibration["end_time_ns_exclusive"])]
    # Initial reference only; no future trajectory/attitude enters propagation.
    row = cal_ref.iloc[0]
    latitude = float(row.latitude_deg)
    earth = earth_rate_enu(latitude)
    q_cal = reference_quaternion(row.roll_deg, row.pitch_deg, row.heading_deg)
    inverse = q_cal * [1, -1, -1, -1]
    earth_body = multiply(multiply(inverse, np.r_[0., earth]), q_cal)[1:]
    # Stationary candidate approximation: mean = fixed offset + initial Earth rate.
    # Keeping Earth in the mean AND compensating Earth again would double count it.
    physical_offset = mean - earth_body
    evaluation_ref = reference.loc[reference.time_ns >= calibration["end_time_ns_exclusive"]]
    variants = [("raw", np.zeros(3), None), ("fixed", mean, None),
                ("earth_only", np.zeros(3), earth), ("fixed_earth", physical_offset, earth)]
    table, reports = None, {}
    for name, offset, navigation_rate in variants:
        measurements = imu.copy()
        measurements[GYRO] = measurements[GYRO] - offset
        current, report = orientation_diagnostic(measurements, evaluation_ref, duration_s,
                                                 max_gap_s, navigation_rate)
        report["gyro_offset_subtracted_xyz_rad_s"] = offset.tolist()
        report["warnings"][0] = "Çıkarılan jiroskop ofseti raporda kayıtlıdır; ölçek/sıcaklık düzeltmesi yok."
        reports[name] = report
        keys = ["time_ns", "elapsed_s", "quality_code"]
        if table is None:
            table = current[keys].copy()
        elif not np.array_equal(table.time_ns, current.time_ns):
            raise ValueError("Karşılaştırma zamanları aynı değil.")
        for column in current.columns:
            if column not in keys:
                table[f"{name}_{column}"] = current[column].to_numpy()
    report = {"status": "fixed_latitude_earth_rate_diagnostic_only", "calibration": calibration,
              "latitude_deg": latitude, "earth_rate_enu_rad_s": earth.tolist(),
              "initial_earth_rate_body_rad_s": earth_body.tolist(),
              "earth_separated_initial_offset_rad_s": physical_offset.tolist(),
              "variants": reports,
              "earth_rotation_scale_deg": float(np.rad2deg(EARTH_RATE_RAD_S * table.elapsed_s.iloc[-1])),
              "warnings": [
                  "Başlangıç duruş adayında yönelim sabit varsayılarak Dünya dönüşü ortalamadan ayrıldı; saf bias etiketi değildir.",
                  "Enlem başlangıçtan sabit tutulur. Taşıma hızı/enlem değişimi yok; hareketli ENU mekanizasyonu değildir.",
                  "Sonraki referans yönelimleri yalnız değerlendirmede kullanılır; kalite kodlarına göre eleme yapılmaz.",
                  "Daha küçük son fark fiziksel doğruluğu tek başına kanıtlamaz; saat/montaj/ölçek belirsizlikleri sürer."]}
    return table, report
