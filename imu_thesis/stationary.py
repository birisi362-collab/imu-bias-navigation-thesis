"""Offline reference-assisted stop inventory and equal-window gyro diagnostics."""

import numpy as np
import pandas as pd

from .audit import audit_data
from .data import ACCEL, GYRO, relative_seconds
from .earth_rate import earth_rate_enu
from .orientation import error_rotation_vector, multiply, reference_quaternion


def analyze_stops(imu, reference, window_s=20., edge_s=1., minimum_stop_s=5.,
                  speed_limit_m_s=.05, angle_limit_deg=.1, max_imu_gap_s=.02):
    parameters = [window_s, minimum_stop_s, speed_limit_m_s, angle_limit_deg, max_imu_gap_s]
    if not np.isfinite(parameters+[edge_s]).all() or min(parameters) <= 0 or edge_s < 0:
        raise ValueError("Süre/eşikler pozitif, kenar süresi negatif olmayan sonlu değerler olmalı.")
    audit, _ = audit_data(imu, reference)
    if audit["errors"]:
        raise ValueError("; ".join(audit["errors"]))
    it = imu.time_ns.to_numpy(dtype=np.int64)
    origin = int(it[0])
    ref = reference.loc[reference.time_ns.between(int(it[0]), int(it[-1]))].reset_index(drop=True)
    times = ref.time_ns.to_numpy(dtype=np.int64)
    speed = np.linalg.norm(ref[[f"velocity_body_{a}_m_s" for a in "xyz"]], axis=1)
    quaternions = np.array([reference_quaternion(r.roll_deg, r.pitch_deg, r.heading_deg)
                            for r in ref.itertuples()])
    # Split on motion or missing reference; do not bridge gaps or merge separate stops.
    runs, start = [], None
    for i, slow in enumerate(speed <= speed_limit_m_s):
        if slow and start is None:
            start = i
        if start is not None and (not slow or i == len(times)-1 or
                                  (i < len(times)-1 and times[i+1]-times[i] > 1_500_000_000)):
            end = i if slow else i-1
            if end > start:
                runs.append((start, end))
            start = None
    inventory, windows = [], []
    for begin, end in runs:
        a, b = int(times[begin]), int(times[end])
        duration = (b-a)/1e9
        if duration < minimum_stop_s:
            continue
        angle = max(np.rad2deg(np.linalg.norm(error_rotation_vector(quaternions[begin], q)))
                    for q in quaternions[begin:end+1])
        overlaps = (it[:-1] < b) & (it[1:] > a)
        max_gap = float(np.diff(it)[overlaps].max()/1e9)
        accepted = angle <= angle_limit_deg and max_gap <= max_imu_gap_s
        item = {"stop_id": len(inventory)+1, "start_time_ns": a, "end_time_ns": b,
                "start_s": (a-origin)/1e9, "end_s": (b-origin)/1e9, "duration_s": duration,
                "maximum_speed_m_s": float(speed[begin:end+1].max()),
                "maximum_rotation_from_first_deg": float(angle), "maximum_imu_gap_s": max_gap,
                "status": "stationary_candidate" if accepted else "rejected",
                "reason": "" if accepted else "Yönelim değişimi veya IMU boşluğu eşiği aşıldı.",
                "equal_window_status": "not_available"}
        inventory.append(item)
        if not accepted:
            continue
        left = a+round(edge_s*1e9)
        right = left+round(window_s*1e9)
        if right > b-round(edge_s*1e9):
            item["equal_window_status"] = "too_short"
            continue
        segment = imu.loc[(imu.time_ns >= left) & (imu.time_ns < right)]
        epochs = ref.loc[(ref.time_ns >= left) & (ref.time_ns < right)]
        if len(segment) < 4 or len(epochs) < 3:
            item["equal_window_status"] = "insufficient_samples"
            continue
        # Use only the first pose in the selected stop window, assuming near rest.
        # This is an offline pose-assisted diagnostic, not a causal IMU stop detector.
        first_ref = epochs.iloc[0]
        q = reference_quaternion(first_ref.roll_deg, first_ref.pitch_deg, first_ref.heading_deg)
        earth = earth_rate_enu(float(first_ref.latitude_deg))
        earth_body = multiply(multiply(q*[1, -1, -1, -1], np.r_[0., earth]), q)[1:]
        half = left+(right-left)//2
        first = segment.loc[segment.time_ns < half, GYRO].mean().to_numpy()-earth_body
        second = segment.loc[segment.time_ns >= half, GYRO].mean().to_numpy()-earth_body
        if not np.isfinite(np.r_[first, second]).all():
            item["equal_window_status"] = "insufficient_half_samples"
            continue
        result = {"stop_id": item["stop_id"], "start_time_ns": left,
                  "end_time_ns_exclusive": right, "start_s": (left-origin)/1e9,
                  "duration_s": window_s, "imu_samples": len(segment),
                  "reference_epochs": len(epochs), "latitude_deg": float(first_ref.latitude_deg),
                  "heading_deg": float(first_ref.heading_deg),
                  "reference_quality_counts": {str(k): int(v) for k,v in epochs.quality_code.value_counts().items()}}
        for i, axis in enumerate("xyz"):
            result[f"raw_mean_{axis}_rad_s"] = float(segment[GYRO[i]].mean())
            result[f"earth_body_{axis}_rad_s"] = float(earth_body[i])
            result[f"offset_candidate_{axis}_rad_s"] = float(segment[GYRO[i]].mean()-earth_body[i])
            result[f"gyro_std_{axis}_rad_s"] = float(segment[GYRO[i]].std(ddof=1))
            result[f"accel_std_{axis}_m_s2"] = float(segment[ACCEL[i]].std(ddof=1))
            result[f"first_half_offset_{axis}_rad_s"] = float(first[i])
            result[f"second_half_offset_{axis}_rad_s"] = float(second[i])
            result[f"second_minus_first_{axis}_rad_s"] = float(second[i]-first[i])
        windows.append(result)
        item["equal_window_status"] = "analyzed"
    motion = pd.DataFrame({"time_ns": times, "elapsed_s": relative_seconds(times, origin),
                           "reference_speed_m_s": speed})
    report = {"status": "offline_reference_assisted_stop_diagnostic", "audit": audit,
              "parameters": {"window_s": window_s, "edge_s": edge_s, "minimum_stop_s": minimum_stop_s,
                             "speed_limit_m_s": speed_limit_m_s, "angle_limit_deg": angle_limit_deg,
                             "max_imu_gap_s": max_imu_gap_s, "max_reference_gap_s": 1.5},
              "inventory": inventory, "equal_windows": windows,
              "candidate_count": sum(r["status"] == "stationary_candidate" for r in inventory),
              "total_candidate_span_s": sum(r["duration_s"] for r in inventory if r["status"] == "stationary_candidate"),
              "warnings": [
                  "Referans hız/yönelim ile çevrim dışı seçim yapıldı; IMU tabanlı canlı duruş algılayıcısı değildir.",
                  "Her uzun duruşun ilk uygun eşit penceresi kullanıldı; ofset/fark sonucuna göre pencere seçilmedi.",
                  "Dünya dönüşü pencerenin ilk referans yöneliminden ayrıldı; yönelim sabit varsayımı yaklaşıktır.",
                  "Küçük dönüş/titreşim, saat, montaj, referans ve sensör hataları aday ofsetlerde kalabilir.",
                  "Duruşlar arası fark saf bias driftini kanıtlamaz; yarı farkları güven aralığı değildir.",
                  "Aralıklı duruşlar birleştirilip sürekli Allan kaydı sayılmaz. Sıcaklık veya bağımsız bias etiketi yok.",
                  "Bu kayıt keşif içindir; aynı duruşlar model eğitimi ve bağımsız test için birlikte kullanılamaz."]}
    return motion, report
