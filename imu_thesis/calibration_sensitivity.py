"""Predeclared calibration lengths, evaluated on one common later interval."""

import numpy as np

from .data import GYRO
from .initial_correction import estimate_initial_offset
from .orientation import orientation_diagnostic


def compare_calibration_lengths(imu, reference, calibration_lengths_s=(3., 5., 10.),
                                duration_s=60., max_gap_s=.02):
    lengths = np.asarray(calibration_lengths_s, dtype=float)
    if (lengths.ndim != 1 or not len(lengths) or not np.isfinite(lengths).all()
            or np.any(lengths <= 0) or len(np.unique(lengths)) != len(lengths)):
        raise ValueError("Kalibrasyon süreleri pozitif, sonlu ve birbirinden farklı olmalı.")
    if len(imu) < 2:
        raise ValueError("En az iki IMU örneği gerekli.")
    # Fixed by the longest REQUESTED window, including windows rejected by rest gates.
    # Thus rejection cannot silently move evaluation earlier.
    common_end = int(imu.time_ns.iloc[0]) + round(float(lengths.max())*1e9)
    evaluation_ref = reference.loc[reference.time_ns >= common_end]
    raw, raw_report = orientation_diagnostic(imu, evaluation_ref, duration_s, max_gap_s)
    keys = ["time_ns", "elapsed_s", "quality_code"]
    table = raw[keys].copy()
    for column in raw.columns:
        if column not in keys:
            table[f"raw_{column}"] = raw[column].to_numpy()
    variants = {}
    for index, length in enumerate(lengths):
        name = f"cal_{index}"
        try:
            mean, calibration = estimate_initial_offset(imu, reference, float(length), max_gap_s)
        except ValueError as exc:
            variants[name] = {"calibration_duration_s": float(length), "status": "rejected",
                              "reason": str(exc)}
            continue
        corrected = imu.copy()
        corrected[GYRO] = corrected[GYRO] - mean
        current, current_report = orientation_diagnostic(corrected, evaluation_ref, duration_s, max_gap_s)
        if not np.array_equal(current.time_ns, table.time_ns):
            raise ValueError("Karşılaştırma zamanları aynı değil.")
        current_report["warnings"][0] = "Sabit başlangıç ortalaması çıkarıldı; Dünya dönüşü ayrıca modellenmedi."
        for column in current.columns:
            if column not in keys:
                table[f"{name}_{column}"] = current[column].to_numpy()
        variants[name] = {"calibration_duration_s": float(length), "status": "accepted_candidate",
                          "calibration": calibration, "evaluation": current_report}
    report = {"status": "calibration_length_sensitivity_only",
              "requested_calibration_lengths_s": lengths.tolist(),
              "common_calibration_end_time_ns_exclusive": common_end,
              "evaluation_start_time_ns": int(table.time_ns.iloc[0]),
              "raw": raw_report, "variants": variants,
              "warnings": [
                  "Süreler sonuçlara göre seçilmez; reddedilen süreler ve nedenleri raporda korunur.",
                  "Pencereler iç içedir; bağımsız tekrar veya istatistiksel güven aralığı değildir.",
                  "Sabit ortalama Dünya dönüşünü ve hareketi de içerebilir; saf fiziksel bias değildir.",
                  "Daha uzun ortalama daha iyi sonuç garantilemez; durağanlık yalnız aday eşikleriyle kontrol edilir.",
                  "Bu deney zamanla değişen biası, öğrenme gerekliliğini veya nihai test performansını kanıtlamaz.",
                  "Sonraki referans yalnız değerlendirmede kullanılır; saat/montaj ve taşıma hızı belirsizlikleri sürer."]}
    return table, report
