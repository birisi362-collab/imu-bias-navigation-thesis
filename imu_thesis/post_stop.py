"""Frozen gyro offsets on disjoint post-stop intervals; offline aided diagnostic."""

import numpy as np
import pandas as pd

from .data import GYRO
from .earth_rate import earth_rate_enu
from .initial_correction import estimate_initial_offset
from .orientation import multiply, orientation_diagnostic, reference_quaternion
from .stationary import analyze_stops


def compare_interval(imu, reference, offsets, start_ns, duration_s=60., max_gap_s=.02):
    """All offsets must be fitted before this interval. No reference resets inside it."""
    if not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("Değerlendirme süresi pozitif ve sonlu olmalı.")
    ref = reference.loc[reference.time_ns >= start_ns]
    if len(ref) < 2:
        raise ValueError("Değerlendirme için referans kapsamı yetersiz.")
    actual_start = int(ref.time_ns.iloc[0])
    end = actual_start+round(duration_s*1e9)
    ref = ref.loc[ref.time_ns <= end]
    if int(ref.time_ns.iloc[-1]) != end or end > int(imu.time_ns.iloc[-1]):
        raise ValueError("Tam değerlendirme süresi için veri yok; süre sessizce kısaltılmadı.")
    if np.any(np.diff(ref.time_ns) > 1_500_000_000):
        raise ValueError("Değerlendirme referansında 1,5 s üzeri boşluk var.")
    earth = earth_rate_enu(float(ref.latitude_deg.iloc[0]))
    table, reports = None, {}
    keys = ["time_ns", "elapsed_s", "quality_code"]
    for name, offset in offsets.items():
        offset = np.asarray(offset, dtype=float)
        if offset.shape != (3,) or not np.isfinite(offset).all():
            raise ValueError("Ofset üç sonlu bileşenden oluşmalı.")
        corrected = imu.copy()
        corrected[GYRO] = corrected[GYRO]-offset
        current, report = orientation_diagnostic(corrected, ref, duration_s, max_gap_s, earth)
        report["gyro_offset_subtracted_xyz_rad_s"] = offset.tolist()
        report["warnings"][0] = "Rapordaki sabit ofset çıkarıldı; Dünya dönüşü bütün yöntemlerde aynı modelle işlendi."
        report["rms_angle_difference_deg"] = float(np.sqrt(np.mean(current.angle_difference_deg.to_numpy()**2)))
        reports[name] = report
        if table is None:
            table = current[keys].copy()
        elif not np.array_equal(table.time_ns, current.time_ns):
            raise ValueError("Karşılaştırma zamanları aynı değil.")
        for column in current.columns:
            if column not in keys:
                table[f"{name}_{column}"] = current[column].to_numpy()
    if table is None:
        raise ValueError("En az bir karşılaştırma yöntemi gerekli.")
    return table, {"start_time_ns": actual_start, "duration_s": duration_s,
                   "earth_rate_enu_rad_s": earth.tolist(), "variants": reports}


def compare_post_stop(imu, reference, duration_s=60., window_s=20., edge_s=1.):
    if not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("Değerlendirme süresi pozitif ve sonlu olmalı.")
    _, inventory = analyze_stops(imu, reference, window_s, edge_s)
    initial_mean, initial_report = estimate_initial_offset(imu, reference, 5.)
    cal = reference.loc[(reference.time_ns >= initial_report["start_time_ns"]) &
                         (reference.time_ns < initial_report["end_time_ns_exclusive"])]
    first = cal.iloc[0]
    q = reference_quaternion(first.roll_deg, first.pitch_deg, first.heading_deg)
    earth = earth_rate_enu(float(first.latitude_deg))
    initial_earth_body = multiply(multiply(q*[1, -1, -1, -1], np.r_[0., earth]), q)[1:]
    initial_offset = initial_mean-initial_earth_body
    initial_report["earth_separated_offset_xyz_rad_s"] = initial_offset.tolist()
    stops = {x["stop_id"]: x for x in inventory["inventory"]}
    experiments, tables = [], []
    for window in inventory["equal_windows"]:
        stop = stops[window["stop_id"]]
        # The immediate next reference sample must indicate departure. Never skip
        # missing reference coverage or wait for a later, better-scoring interval.
        after = reference.loc[reference.time_ns > stop["end_time_ns"]]
        entry = {"stop_id": stop["stop_id"], "calibration_window": window,
                 "stop_end_time_ns": stop["end_time_ns"]}
        experiments.append(entry)
        if after.empty or int(after.time_ns.iloc[0])-stop["end_time_ns"] > 1_500_000_000:
            entry.update(status="skipped", reason="Duruş sonrasında kesintisiz referans yok.")
            continue
        departure = after.iloc[0]
        speed = np.linalg.norm([departure[f"velocity_body_{a}_m_s"] for a in "xyz"])
        if speed <= inventory["parameters"]["speed_limit_m_s"]:
            entry.update(status="skipped", reason="Sonraki referansta hareket başlamadı.")
            continue
        evaluation_start = int(departure.time_ns)
        if max(window["end_time_ns_exclusive"], initial_report["end_time_ns_exclusive"]) > evaluation_start:
            raise ValueError("Kalibrasyon değerlendirmeyle örtüşüyor.")
        offsets = {"no_offset": np.zeros(3), "initial": initial_offset,
                   "recent": np.array([window[f"offset_candidate_{a}_rad_s"] for a in "xyz"])}
        try:
            table, report = compare_interval(imu, reference, offsets, evaluation_start, duration_s)
        except ValueError as exc:
            entry.update(status="skipped", reason=str(exc))
            continue
        table.insert(0, "stop_id", stop["stop_id"])
        tables.append(table)
        entry.update(status="evaluated", evaluation=report)
    report = {"status": "offline_reference_assisted_post_stop_comparison", "duration_s": duration_s,
              "initial_calibration": initial_report, "stop_analysis": inventory, "experiments": experiments,
              "warnings": [
                  "Duruş/hareket seçimi çevrim dışı referans desteklidir; gerçek zamanlı IMU duruş algılayıcısı değildir.",
                  "Ofsetler değerlendirmeden önceki veriden hesaplanıp sabitlendi; aralık içinde güncellenmez.",
                  "Her deney aynı başlangıç referans yöneliminden bir kez başlar; deneyler arasında durum taşınmaz.",
                  "Değerlendirme referansının sonraki yönelimleri yalnız hata ölçümünde kullanılır.",
                  "Bütün hesaplarda başlangıç enlemiyle aynı Dünya dönüşü modeli var; taşıma hızı yok.",
                  "İlk 5 s ile güncel 20 s hem süre hem zaman bakımından farklıdır; üstünlük bias driftini tek başına kanıtlamaz.",
                  "Bu kayıt keşif içindir; sonuçlar bağımsız test veya öğrenilmiş model başarımı değildir."]}
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(), report
