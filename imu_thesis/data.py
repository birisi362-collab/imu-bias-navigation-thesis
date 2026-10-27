"""UrbanNav Medium-Urban-1 readers. No calibration is silently applied here."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import pandas as pd


GYRO = [f"gyro_{axis}_rad_s" for axis in "xyz"]
ACCEL = [f"accel_{axis}_m_s2" for axis in "xyz"]
REFERENCE_FIELDS = [
    "utc_time", "gps_week", "gps_time", "lat_d", "lat_m", "lat_s",
    "lon_d", "lon_m", "lon_s", "height_m", "velocity_body_x_m_s",
    "velocity_body_y_m_s", "velocity_body_z_m_s", "accel_body_x_m_s2",
    "accel_body_y_m_s2", "accel_body_z_m_s2", "roll_deg", "pitch_deg",
    "heading_deg", "quality_code",
]


def seconds_to_ns(value: str) -> int:
    """Convert decimal seconds without losing precision at Unix-epoch scale."""
    try:
        ns = Decimal(str(value)) * Decimal(1_000_000_000)
        if not ns.is_finite() or ns != ns.to_integral_value():
            raise ValueError("Zaman en fazla nanosaniye hassasiyetinde olmalı.")
        result = int(ns)
    except (InvalidOperation, OverflowError) as exc:
        raise ValueError(f"Geçersiz zaman: {value}") from exc
    if not -(2**63) <= result < 2**63:
        raise ValueError("Zaman int64 aralığının dışında.")
    return result


def relative_seconds(time_ns, origin_ns: int) -> np.ndarray:
    # Subtract integers FIRST; converting epoch nanoseconds to float first loses bits.
    return (np.asarray(time_ns, dtype=np.int64) - np.int64(origin_ns)).astype(float) / 1e9


def dms_to_degrees(degrees: str, minutes: str, seconds: str, limit: int) -> float:
    d, m, s = float(degrees), float(minutes), float(seconds)
    if not np.isfinite([d, m, s]).all() or not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError("Geçersiz derece/dakika/saniye koordinatı.")
    result = abs(d) + m / 60 + s / 3600
    if result > limit:
        raise ValueError("Koordinat aralık dışında.")
    return -result if degrees.startswith("-") else result


def read_imu(path: str | Path, time_column: str = "field.header.stamp") -> pd.DataFrame:
    """Read sensor angular velocity / specific force, NOT its AHRS orientation."""
    mapping = {
        **{f"field.angular_velocity.{a}": GYRO[i] for i, a in enumerate("xyz")},
        **{f"field.linear_acceleration.{a}": ACCEL[i] for i, a in enumerate("xyz")},
    }
    columns = [time_column, *mapping]
    try:
        frame = pd.read_csv(path, usecols=columns, dtype={time_column: "int64"})
    except (ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"IMU CSV sütunları veya zaman biçimi geçersiz: {exc}") from exc
    frame = frame.rename(columns={time_column: "time_ns", **mapping})
    for column in GYRO + ACCEL:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if len(frame) < 2:
        raise ValueError("IMU dosyasında en az iki örnek gerekli.")
    return frame[["time_ns", *GYRO, *ACCEL]]


def read_reference(path: str | Path, time_offset_s: str = "0") -> pd.DataFrame:
    """Read UrbanNav SPAN-CPT + IE text, whose lat/lon each occupy THREE fields.

    UTC seconds are used for time matching, not GPS seconds-of-week. The meaning
    of quality_code is deliberately not guessed; it remains a source field.
    """
    records = []
    offset_ns = seconds_to_ns(time_offset_s)
    with Path(path).open(encoding="utf-8-sig") as handle:
        header = handle.readline()
        units = handle.readline()
        if not all(word in header.split() for word in ["UTCTime", "Latitude", "Heading", "Q"]):
            raise ValueError("Beklenen UrbanNav referans başlığı bulunamadı.")
        if "(sec)" not in units or "(deg)" not in units:
            raise ValueError("Referans birim satırı beklenen biçimde değil.")
        for line_number, line in enumerate(handle, start=3):
            if not line.strip():
                continue
            values = line.split()
            if len(values) != len(REFERENCE_FIELDS):
                raise ValueError(f"Referans satır {line_number}: 20 alan bekleniyor, {len(values)} bulundu.")
            fields = dict(zip(REFERENCE_FIELDS, values))
            try:
                record = {key: float(value) for key, value in fields.items()}
                if not np.isfinite(list(record.values())).all():
                    raise ValueError("Sonlu olmayan değer")
                time_ns = seconds_to_ns(fields["utc_time"]) + offset_ns
                if not -(2**63) <= time_ns < 2**63:
                    raise ValueError("Zaman int64 aralığının dışında")
                record["time_ns"] = time_ns
                record["latitude_deg"] = dms_to_degrees(fields["lat_d"], fields["lat_m"], fields["lat_s"], 90)
                record["longitude_deg"] = dms_to_degrees(fields["lon_d"], fields["lon_m"], fields["lon_s"], 180)
                records.append(record)
            except ValueError as exc:
                raise ValueError(f"Referans satır {line_number}: {exc}") from exc
    if len(records) < 2:
        raise ValueError("Referans dosyasında en az iki örnek gerekli.")
    result = pd.DataFrame(records).drop(columns=["utc_time", "lat_d", "lat_m", "lat_s", "lon_d", "lon_m", "lon_s"])
    result["time_ns"] = np.asarray([r["time_ns"] for r in records], dtype=np.int64)
    return result
