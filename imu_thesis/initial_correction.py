"""A fixed initial gyro-offset diagnostic, with disjoint calibration/evaluation."""

import numpy as np

from .data import ACCEL, GYRO
from .orientation import error_rotation_vector, orientation_diagnostic, reference_quaternion


def estimate_initial_offset(imu, reference, calibration_duration_s=5., max_gap_s=.02):
    """Use [first IMU stamp, first stamp+duration); reference only checks rest.

    Thresholds are fixed diagnostic gates, not a validated stationary detector.
    The mean includes Earth rate, possible motion and other errors, not pure bias.
    """
    if not np.isfinite(calibration_duration_s) or calibration_duration_s <= 0:
        raise ValueError("Başlangıç düzeltmesi süresi pozitif olmalı.")
    if not np.isfinite(max_gap_s) or max_gap_s <= 0:
        raise ValueError("Zaman boşluğu sınırı pozitif olmalı.")
    for name, frame in [("IMU", imu), ("Referans", reference)]:
        if len(frame) < 2 or np.any(np.diff(frame.time_ns.to_numpy(dtype=np.int64)) <= 0):
            raise ValueError(f"{name} zamanları kesin artan olmalı.")
    start = int(imu.time_ns.iloc[0])
    end = start+round(calibration_duration_s*1e9)
    if end > int(imu.time_ns.iloc[-1]):
        raise ValueError("Başlangıç düzeltmesi aralığı IMU kapsamını aşıyor.")
    cal = imu.loc[(imu.time_ns >= start) & (imu.time_ns < end)]
    if len(cal) < 4:
        raise ValueError("Başlangıç düzeltmesi için yeterli IMU örneği yok.")
    # Include the original interval crossing the calibration end boundary.
    times = imu.time_ns.to_numpy(dtype=np.int64)
    overlap = (times[:-1] < end) & (times[1:] > start)
    if np.any(np.diff(times)[overlap]/1e9 > max_gap_s):
        raise ValueError("Başlangıç düzeltmesi aralığında büyük IMU boşluğu var.")
    if not np.isfinite(cal[GYRO+ACCEL].to_numpy()).all():
        raise ValueError("Başlangıç ölçümleri sonlu olmalı.")
    ref = reference.loc[(reference.time_ns >= start) & (reference.time_ns < end)]
    coverage = 0. if len(ref)<2 else int(ref.time_ns.iloc[-1]-ref.time_ns.iloc[0])/1e9
    if len(ref)<3 or coverage < .6*calibration_duration_s:
        raise ValueError("Duruş kontrolü için başlangıç aralığında yeterli referans kapsamı yok.")
    speed_cols = [f"velocity_body_{a}_m_s" for a in "xyz"]
    if not np.isfinite(ref[speed_cols+["roll_deg", "pitch_deg", "heading_deg"]].to_numpy()).all():
        raise ValueError("Başlangıç referansı sonlu olmalı.")
    speed = np.linalg.norm(ref[speed_cols].to_numpy(), axis=1)
    qs = [reference_quaternion(row.roll_deg, row.pitch_deg, row.heading_deg) for row in ref.itertuples()]
    angles = np.rad2deg([np.linalg.norm(error_rotation_vector(qs[0], q)) for q in qs])
    if speed.max() > .05 or angles.max() > .1:
        raise ValueError("Başlangıç aralığı duruş adayı sınırlarını geçemedi; otomatik düzeltme uygulanmadı.")
    halfway = start+(end-start)//2
    first = cal.loc[cal.time_ns < halfway, GYRO]
    second = cal.loc[cal.time_ns >= halfway, GYRO]
    if len(first)<2 or len(second)<2:
        raise ValueError("İki yarıda en az ikişer IMU örneği gerekli.")
    mean = cal[GYRO].mean().to_numpy()
    norms = np.linalg.norm(cal[ACCEL].to_numpy(), axis=1)
    report = {"status": "stationary_candidate_only", "start_time_ns": start,
              "end_time_ns_exclusive": end, "duration_s": calibration_duration_s,
              "imu_samples": len(cal), "reference_epochs": len(ref),
              "reference_coverage_s": coverage, "maximum_reference_speed_m_s": float(speed.max()),
              "maximum_reference_orientation_change_deg": float(angles.max()),
              "gates": {"maximum_speed_m_s": .05, "maximum_orientation_change_deg": .1,
                        "minimum_reference_epochs": 3, "minimum_reference_span_fraction": .6},
              "gyro_offset_xyz_rad_s": mean.tolist(),
              "gyro_sample_std_xyz_rad_s": cal[GYRO].std(ddof=1).to_list(),
              "first_half_gyro_mean_xyz_rad_s": first.mean().to_list(),
              "second_half_gyro_mean_xyz_rad_s": second.mean().to_list(),
              "second_minus_first_mean_xyz_rad_s": (second.mean()-first.mean()).to_list(),
              "accel_norm_mean_m_s2": float(norms.mean()),
              "accel_norm_sample_std_m_s2": float(norms.std(ddof=1)),
              "warnings": [
                  "Referans hız/yönelim kontrolü durağanlığı kanıtlamaz; 1 Hz referans titreşimleri kaçırabilir.",
                  "Örnek ortalaması saf fiziksel bias değildir: Dünya dönüşü ve küçük hareketler de içerebilir.",
                  "Kısa aralık uzun dönem stokastik kalibrasyon/Allan analizi yerine geçmez.",
                  "Ardışık örnekler bağımsız varsayılmadı; std/sqrt(N) ile kesinlik iddiası yapılmadı.",
                  "İki yarının farkı gerçek bias değişimini tek başına göstermez."]}
    return mean, report


def compare_initial_correction(imu, reference, calibration_duration_s=5., duration_s=60., max_gap_s=.02):
    offset, calibration = estimate_initial_offset(imu, reference, calibration_duration_s, max_gap_s)
    # No calibration sample or reference epoch is used in evaluation.
    evaluation_ref = reference.loc[reference.time_ns >= calibration["end_time_ns_exclusive"]]
    corrected = imu.copy()
    corrected[GYRO] = corrected[GYRO]-offset
    raw_table, raw_report = orientation_diagnostic(imu, evaluation_ref, duration_s, max_gap_s)
    fixed_table, fixed_report = orientation_diagnostic(corrected, evaluation_ref, duration_s, max_gap_s)
    if not np.array_equal(raw_table.time_ns.to_numpy(), fixed_table.time_ns.to_numpy()):
        raise ValueError("Karşılaştırma zamanları aynı değil.")
    columns = ["time_ns", "elapsed_s", "quality_code"]
    result = raw_table[columns].copy()
    for prefix, table in [("raw", raw_table), ("fixed", fixed_table)]:
        for column in table.columns:
            if column not in columns:
                result[f"{prefix}_{column}"] = table[column].to_numpy()
    # Replace the raw-only wording inherited from the generic diagnostic.
    fixed_report["warnings"][0] = "Yalnız başlangıç jiroskop ortalaması çıkarıldı; ölçek/ısı düzeltmesi yok."
    report = {"status": "diagnostic_comparison_only", "calibration": calibration,
              "raw": raw_report, "fixed_initial_offset": fixed_report,
              "protocol": "İlk IMU zamanından itibaren sabit başlangıç aralığı; sonra aynı başlangıç yönelimi ve süre.",
              "warnings": ["Süre/eşikler son değerlendirme farkını küçültmek için ayarlanmamalı.",
                           "Önceki ham deneyin başlangıcı farklıdır; yalnız bu çalıştırmadaki iki eğri karşılaştırılır.",
                           "Tek kısa kayıt çevrim içi öğrenme gerekliliğini veya model üstünlüğünü kanıtlamaz."]}
    return result, report
