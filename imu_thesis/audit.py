"""Descriptive data checks, not a certification of reference accuracy."""

import numpy as np
import pandas as pd

from .data import GYRO, ACCEL


def timing_statistics(time_ns) -> dict:
    times = np.asarray(time_ns, dtype=np.int64)
    intervals = np.diff(times).astype(float) / 1e9
    positive = intervals[intervals > 0]
    median = float(np.median(positive)) if len(positive) else None
    return {
        "samples": len(times), "first_time_ns": int(times[0]), "last_time_ns": int(times[-1]),
        "duration_s": float((int(times[-1]) - int(times[0])) / 1e9),
        "duplicate_steps": int(np.sum(intervals == 0)),
        "backward_steps": int(np.sum(intervals < 0)),
        "median_dt_s": median,
        "median_rate_hz": 1 / median if median else None,
        "max_positive_dt_s": float(positive.max()) if len(positive) else None,
        "gaps_over_3x_median": int(np.sum(intervals > 3 * median)) if median else None,
    }


def audit_data(imu: pd.DataFrame, reference: pd.DataFrame, tolerance_s: float = .01):
    """Pair each overlapping reference epoch to its nearest actual IMU sample.

    This is only a temporal proximity check. It does not estimate clock offset,
    correct frame rotations, or turn the IMU into a reference sensor.
    """
    if not np.isfinite(tolerance_s) or tolerance_s <= 0:
        raise ValueError("Zaman eşleme toleransı pozitif olmalı.")
    report = {
        "stage": "01_data_inspection", "imu": timing_statistics(imu.time_ns),
        "reference": timing_statistics(reference.time_ns), "errors": [], "warnings": [],
        "reference_quality_counts": {str(k): int(v) for k, v in reference.quality_code.value_counts().items()},
    }
    for name, frame, columns in [("imu", imu, GYRO + ACCEL), ("reference", reference, [c for c in reference if c != "time_ns"])]:
        stats = report[name]
        nonfinite = int((~np.isfinite(frame[columns].to_numpy(dtype=float))).sum())
        stats["nonfinite_values"] = nonfinite
        if stats["duplicate_steps"] or stats["backward_steps"]:
            report["errors"].append(f"{name}: Zamanlar kesin artmıyor; otomatik sıralama/silme yapılmadı.")
        if nonfinite:
            report["errors"].append(f"{name}: {nonfinite} sonlu olmayan ölçüm değeri var.")
        if stats["gaps_over_3x_median"]:
            report["warnings"].append(f"{name}: Medyan örnek aralığının üç katını aşan zaman boşlukları var.")
    start = max(int(imu.time_ns.min()), int(reference.time_ns.min()))
    end = min(int(imu.time_ns.max()), int(reference.time_ns.max()))
    report["overlap"] = {"start_ns": start, "end_ns": end, "duration_s": max(0, (end - start) / 1e9)}
    empty = pd.DataFrame()
    if end <= start:
        report["errors"].append("IMU ile referansın zaman kapsamları örtüşmüyor.")
    if report["errors"]:
        return report, empty
    ref = reference.loc[reference.time_ns.between(start, end)].reset_index(drop=True).copy()
    if ref.empty:
        report["errors"].append("Örtüşme içinde referans örneği yok.")
        return report, empty
    it = imu.time_ns.to_numpy(dtype=np.int64)
    rt = ref.time_ns.to_numpy(dtype=np.int64)
    right = np.searchsorted(it, rt).clip(0, len(it) - 1)
    left = np.maximum(right - 1, 0)
    indices = np.where(np.abs(it[left] - rt) <= np.abs(it[right] - rt), left, right)
    difference_ns = it[indices] - rt
    matched = np.abs(difference_ns.astype(float)) / 1e9 <= tolerance_s
    paired = ref.copy()
    paired["nearest_imu_time_ns"] = pd.array([int(it[i]) if ok else pd.NA for i, ok in zip(indices, matched)], dtype="Int64")
    paired["time_offset_ms"] = np.where(matched, difference_ns / 1e6, np.nan)
    for column in GYRO + ACCEL:
        paired[column] = np.where(matched, imu[column].to_numpy()[indices], np.nan)
    report["time_matching"] = {
        "method": "nearest actual IMU sample, no extrapolation",
        "tolerance_s": tolerance_s, "reference_epochs_in_overlap": len(ref),
        "matched": int(matched.sum()), "unmatched": int((~matched).sum()),
        "reference_epochs_outside_overlap": len(reference) - len(ref),
        "max_abs_offset_ms": float(np.abs(difference_ns[matched]).max() / 1e6) if matched.any() else None,
    }
    if not matched.all():
        report["warnings"].append("Bazı referans anlarında tolerans içinde IMU yok; bu satırlarda IMU alanları boş bırakıldı.")
    report["warnings"].extend([
        "Zaman yakınlığı, saat senkronizasyonunun fiziksel olarak doğrulandığı anlamına gelmez.",
        "Referans Q kodları raporlandı; anlamı doğrulanmadan RTK fixed/float diye yorumlanmadı.",
        "Eksen dönüşümleri ve sensörler arası montaj farkları bu aşamada uygulanmadı.",
        "IMU'nun orientation alanı referans olarak kullanılmadı. Bias etiketi üretilmedi.",
    ])
    return report, paired
