"""Quaternion orientation diagnostic; not a complete GNSS/INS mechanization.

Hamilton multiplication, scalar-first [w,x,y,z], active body-to-ENU rotation.
UrbanNav nominal body: x-right, y-forward, z-up. IE convention:
R_body_to_ENU = Rz(-heading) Rx(pitch) Ry(roll).
"""

import numpy as np
import pandas as pd

from .data import GYRO, relative_seconds


def unit_quaternion(q):
    q = np.asarray(q, dtype=float)
    norm = np.linalg.norm(q)
    if q.shape != (4,) or not np.isfinite(q).all() or norm < 1e-15:
        raise ValueError("Quaternion dört sonlu bileşenden oluşmalı ve sıfır olmamalı.")
    return q / norm


def multiply(a, b):
    """Hamilton product: R(a*b) = R(a) R(b)."""
    w, x, y, z = a
    v, i, j, k = b
    return np.array([w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j,
                     w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v])


def from_rotation_vector(vector):
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError("Dönüş vektörü üç sonlu bileşen içermeli.")
    angle = np.linalg.norm(vector)
    # np.sinc(x) = sin(pi*x)/(pi*x); stable also at zero.
    return np.r_[np.cos(angle/2), .5*np.sinc(angle/(2*np.pi))*vector]


def reference_quaternion(roll_deg, pitch_deg, heading_deg):
    """IE body-to-local-level convention, NOT generic XYZ Euler conversion."""
    r, p, h = np.deg2rad([roll_deg, pitch_deg, heading_deg])
    return unit_quaternion(multiply(multiply(from_rotation_vector([0, 0, -h]),
                                            from_rotation_vector([p, 0, 0])),
                                    from_rotation_vector([0, r, 0])))


def error_rotation_vector(reference, estimate):
    """Shortest relative rotation, in reference body axes; invariant to q sign."""
    inverse = unit_quaternion(reference) * [1, -1, -1, -1]
    error = unit_quaternion(multiply(inverse, unit_quaternion(estimate)))
    if error[0] < 0:
        error = -error
    sine = np.linalg.norm(error[1:])
    if sine < 1e-12:
        return 2*error[1:]
    return 2*np.arctan2(sine, error[0])*error[1:]/sine


def integrate_at_epochs(imu_time_ns, gyro_rad_s, epoch_time_ns, initial_q,
                        max_gap_s=.02):
    """Use every IMU interval; interpolate rates only inside measured support.

    Epoch boundaries split original intervals. Rate is linear within an interval;
    each subinterval uses its average rate and a quaternion exponential. No
    reference orientation enters propagation after initial_q. This offline rate
    quadrature is not a claim of zero-latency streaming implementation.
    """
    for name, times in [("IMU", imu_time_ns), ("Referans", epoch_time_ns)]:
        times = np.asarray(times)
        if times.dtype.kind not in "iu" or times.ndim != 1 or len(times) < 2:
            raise ValueError(f"{name}: en az iki tamsayı nanosaniye zamanı gerekli.")
        if np.any(np.diff(times) <= 0):
            raise ValueError(f"{name} zamanları kesin artan olmalı.")
    imu_time_ns = np.asarray(imu_time_ns, dtype=np.int64)
    epoch_time_ns = np.asarray(epoch_time_ns, dtype=np.int64)
    gyro = np.asarray(gyro_rad_s, dtype=float)
    if gyro.shape != (len(imu_time_ns), 3) or not np.isfinite(gyro).all():
        raise ValueError("Jiroskop dizisi Nx3 sonlu değer içermeli.")
    if not np.isfinite(max_gap_s) or max_gap_s <= 0:
        raise ValueError("En büyük zaman boşluğu pozitif olmalı.")
    start, end = epoch_time_ns[[0, -1]]
    if start < imu_time_ns[0] or end > imu_time_ns[-1]:
        raise ValueError("Referans anları IMU kapsamının dışında; dışa değerleme yapılmaz.")
    # Check original gaps, including the gaps containing the two boundaries.
    overlaps = (imu_time_ns[:-1] < end) & (imu_time_ns[1:] > start)
    original_dt = np.diff(imu_time_ns)[overlaps].astype(float)/1e9
    if np.any(original_dt > max_gap_s):
        raise ValueError("IMU zaman boşluğu sınırı aşıldı; eksik veriyle entegrasyon durduruldu.")
    selected = (imu_time_ns >= start) & (imu_time_ns <= end)
    timeline = np.union1d(imu_time_ns[selected], epoch_time_ns)
    seconds = relative_seconds(timeline, int(start))
    imu_seconds = relative_seconds(imu_time_ns, int(start))
    rates = np.column_stack([np.interp(seconds, imu_seconds, gyro[:, k]) for k in range(3)])
    positions = np.searchsorted(timeline, epoch_time_ns)
    result = np.empty((len(epoch_time_ns), 4))
    q = unit_quaternion(initial_q)
    result[0] = q
    next_epoch = 1
    for index, dt in enumerate(np.diff(timeline).astype(float)/1e9, start=1):
        delta = from_rotation_vector(.5*(rates[index-1]+rates[index])*dt)
        q = unit_quaternion(multiply(q, delta))
        if next_epoch < len(positions) and index == positions[next_epoch]:
            result[next_epoch] = q
            next_epoch += 1
    return result, {"imu_samples_in_closed_interval": int(selected.sum()),
                    "integration_steps": len(timeline)-1,
                    "maximum_original_imu_dt_s": float(original_dt.max())}


def orientation_diagnostic(imu, reference, duration_s=60., max_gap_s=.02):
    if not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("Süre pozitif ve sonlu olmalı.")
    for name, frame in [("IMU", imu), ("Referans", reference)]:
        if len(frame) < 2 or np.any(np.diff(frame.time_ns.to_numpy(dtype=np.int64)) <= 0):
            raise ValueError(f"{name} zamanları kesin artan olmalı.")
    valid = reference.loc[(reference.time_ns >= int(imu.time_ns.iloc[0])) &
                          (reference.time_ns <= int(imu.time_ns.iloc[-1]))].copy()
    if valid.empty:
        raise ValueError("Ortak zaman kapsamı yok.")
    start = int(valid.time_ns.iloc[0])
    valid = valid.loc[valid.time_ns <= start+round(duration_s*1e9)]
    if len(valid) < 2:
        raise ValueError("Seçilen sürede en az iki referans anı gerekli.")
    q_ref = np.array([reference_quaternion(row.roll_deg, row.pitch_deg, row.heading_deg)
                      for row in valid.itertuples()])
    q_est, counts = integrate_at_epochs(imu.time_ns.to_numpy(), imu[GYRO].to_numpy(),
                                       valid.time_ns.to_numpy(), q_ref[0], max_gap_s)
    vectors = np.rad2deg(np.array([error_rotation_vector(r, e) for r, e in zip(q_ref, q_est)]))
    angles = np.linalg.norm(vectors, axis=1)
    table = pd.DataFrame({"time_ns": valid.time_ns.to_numpy(dtype=np.int64),
                          "elapsed_s": relative_seconds(valid.time_ns, start),
                          "angle_difference_deg": angles,
                          "quality_code": valid.quality_code.to_numpy()})
    for k, axis in enumerate("wxyz"):
        table[f"estimated_q_{axis}"] = q_est[:, k]
        table[f"reference_q_{axis}"] = q_ref[:, k]
    for k, axis in enumerate("xyz"):
        table[f"difference_rotvec_{axis}_deg"] = vectors[:, k]
    report = {"status": "diagnostic_only", "quaternion_order": "w,x,y,z (Hamilton)",
              "rotation": "body_to_ENU", "reference_conversion": "Rz(-heading) Rx(pitch) Ry(roll)",
              "initialization": "first reference epoch in overlap, used once",
              "start_time_ns": start, "duration_s": float(table.elapsed_s.iloc[-1]),
              "reference_epochs": len(table), **counts,
              "final_angle_difference_deg": float(angles[-1]),
              "maximum_angle_difference_deg": float(angles.max()),
              "max_quaternion_norm_error": float(np.abs(np.linalg.norm(q_est, axis=1)-1).max()),
              "warnings": [
                  "Ham jiroskop; bias/ölçek/ısı düzeltmesi uygulanmadı.",
                  "Dünya dönüşü ve yerel çerçevenin taşıma hızı henüz çıkarılmadı; bu tam INS mekanizasyonu değildir.",
                  "Kaynağın nominal IMU-SPAN yön hizası kullanıldı; gerçek montaj hatası doğrulanmış değildir.",
                  "Zaman damgaları kullanıldı; fiziksel saat ofseti/drifti kalibre edilmiş değildir.",
                  "Referans bir kestirimdir; Q grupları elenmedi, fark fiziksel bias etiketi değildir.",
                  "Öteleme yönelimi değiştirmez; konum/hız lever arm düzeltmesi bu deneyin kapsamında değildir.",
                  "Referans yalnız başlangıçta ve değerlendirmede kullanılır; GNSS/ESKF/öğrenme henüz yok."]}
    return table, report
