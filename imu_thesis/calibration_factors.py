"""Separate calibration age and averaging length on identical future intervals."""

import numpy as np
import pandas as pd

from .post_stop import compare_interval
from .stationary import analyze_stops


def compare_calibration_factors(imu, reference, duration_s=60., short_s=5., long_s=20., edge_s=1.):
    if (not np.isfinite([duration_s, short_s, long_s, edge_s]).all()
            or duration_s <= 0 or not 0 < short_s < long_s or edge_s < 0):
        raise ValueError("Süreler pozitif, kısa süre uzundan küçük, kenar süresi negatif olmayan sonlu değerler olmalı.")
    _, long_report = analyze_stops(imu, reference, long_s, edge_s)
    _, short_report = analyze_stops(imu, reference, short_s, edge_s)
    short_windows = {w["stop_id"]: w for w in short_report["equal_windows"]}
    long_windows = long_report["equal_windows"]
    if not long_windows:
        raise ValueError("Uzun kalibrasyon penceresine uygun duruş yok.")
    baseline = long_windows[0]
    if baseline["stop_id"] not in short_windows:
        raise ValueError("İlk uzun duruşta kısa pencere yok.")
    old = {"short": short_windows[baseline["stop_id"]], "long": baseline}
    stops = {s["stop_id"]: s for s in long_report["inventory"]}
    experiments, tables = [], []
    # At the first long stop old/recent are identical by construction; do not
    # count it as an independent observation in favor of either method.
    for recent_long in long_windows[1:]:
        sid = recent_long["stop_id"]
        entry = {"stop_id": sid}
        experiments.append(entry)
        if sid not in short_windows:
            entry.update(status="skipped", reason="Aynı duruşta kısa kalibrasyon yok.")
            continue
        recent = {"short": short_windows[sid], "long": recent_long}
        stop = stops[sid]
        after = reference.loc[reference.time_ns > stop["end_time_ns"]]
        if after.empty or int(after.time_ns.iloc[0])-stop["end_time_ns"] > 1_500_000_000:
            entry.update(status="skipped", reason="Duruş sonrasında kesintisiz referans yok.")
            continue
        departure = after.iloc[0]
        if np.linalg.norm([departure[f"velocity_body_{a}_m_s"] for a in "xyz"]) <= .05:
            entry.update(status="skipped", reason="Sonraki referansta hareket başlamadı.")
            continue
        start = int(departure.time_ns)
        windows = {"old_short": old["short"], "old_long": old["long"],
                   "recent_short": recent["short"], "recent_long": recent["long"]}
        if any(w["end_time_ns_exclusive"] > start for w in windows.values()):
            raise ValueError("Kalibrasyon değerlendirmeyle örtüşüyor.")
        offsets = {name: np.array([w[f"offset_candidate_{a}_rad_s"] for a in "xyz"])
                   for name, w in windows.items()}
        entry["calibrations"] = windows
        try:
            table, evaluation = compare_interval(imu, reference, offsets, start, duration_s)
        except ValueError as exc:
            entry.update(status="skipped", reason=str(exc))
            continue
        table.insert(0, "stop_id", sid)
        tables.append(table)
        entry.update(status="evaluated", evaluation=evaluation)
    report = {"status": "offline_calibration_age_length_control", "duration_s": duration_s,
              "short_s": short_s, "long_s": long_s, "edge_s": edge_s,
              "baseline_stop_id": baseline["stop_id"], "baseline_calibrations": old,
              "stop_analysis": long_report, "experiments": experiments,
              "warnings": [
                  "Eski kalibrasyon kaydın ilk 5 s'si değil, ilk UZUN duruştur; önceki deneyin baseline'ı değişti.",
                  "Eski pencere bütün deneylerde sabit; her duruşun ilk uygun 5/20 s pencereleri kullanılır.",
                  "İlk uzun duruşta eski ve güncel aynıdır; bu durum iyileşme deneyi olarak sayılmadı.",
                  "Duruş seçimi çevrim dışı referans desteklidir; canlı duruş algılayıcısı değildir.",
                  "Dört hesapta aynı ilk referans yönelimi, değerlendirme süresi ve Dünya dönüşü modeli kullanılır.",
                  "Dört ofset değerlendirme başlamadan hesaplanır ve sabitlenir; sonraki referans yalnız farkı ölçer.",
                  "Süre etkisi 5/20 s, güncellik etkisi eski/güncel karşılaştırmasıdır; sonuçlar küçük keşif örneklemidir.",
                  "Güncellik etkisi sıcaklık veya saf fiziksel bias drifti kanıtı değildir; taşıma hızı/zaman/montaj sınırları sürer."]}
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(), report
