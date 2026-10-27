"""Non-interactive quick-look figures. All calculations use the complete input."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .data import GYRO, ACCEL, relative_seconds


def make_plots(imu, reference, output: Path, max_points: int = 12000):
    if max_points < 2:
        raise ValueError("Çizim için en az iki nokta gerekli.")
    origin = min(int(imu.time_ns.iloc[0]), int(reference.time_ns.iloc[0]))
    times = relative_seconds(imu.time_ns, origin)
    rt = relative_seconds(reference.time_ns, origin)
    selected = np.unique(np.linspace(0, len(imu) - 1, min(len(imu), max_points), dtype=int))
    fig, axes = plt.subplots(3, 2, figsize=(12, 8), sharex=True, constrained_layout=True)
    for i, axis in enumerate("xyz"):
        axes[i, 0].plot(times[selected], imu[GYRO[i]].to_numpy()[selected], lw=.6)
        axes[i, 1].plot(times[selected], imu[ACCEL[i]].to_numpy()[selected], lw=.6)
        axes[i, 0].set_ylabel(f"Gyro {axis} (rad/s)")
        axes[i, 1].set_ylabel(f"Accel {axis} (m/s²)")
    for ax in axes.flat:
        ax.grid(alpha=.25)
    axes[-1, 0].set_xlabel("Time from common origin (s)")
    axes[-1, 1].set_xlabel("Time from common origin (s)")
    fig.suptitle("UrbanNav IMU measurements (plot subsampled only)")
    fig.savefig(output / "imu_signals.png", dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
    axes[0, 0].plot(rt, np.rad2deg(np.unwrap(np.deg2rad(reference.heading_deg))))
    axes[0, 0].set(xlabel="Time (s)", ylabel="Reference heading, unwrapped (deg)")
    axes[0, 1].plot(rt, reference.roll_deg, label="Roll")
    axes[0, 1].plot(rt, reference.pitch_deg, label="Pitch")
    axes[0, 1].set(xlabel="Time (s)", ylabel="Reference attitude (deg)")
    axes[0, 1].legend()
    speed = np.linalg.norm(reference[[f"velocity_body_{a}_m_s" for a in "xyz"]], axis=1)
    axes[1, 0].plot(rt, speed)
    axes[1, 0].set(xlabel="Time (s)", ylabel="Reference speed magnitude (m/s)")
    lat = np.deg2rad(reference.latitude_deg.to_numpy())
    lon = np.deg2rad(reference.longitude_deg.to_numpy())
    # Small-area equirectangular projection for visualization, not final metrics.
    east = 6378137 * np.cos(lat[0]) * (lon - lon[0])
    north = 6378137 * (lat - lat[0])
    axes[1, 1].plot(east, north)
    axes[1, 1].set(xlabel="Approx. east (m)", ylabel="Approx. north (m)", aspect="equal")
    for ax in axes.flat:
        ax.grid(alpha=.25)
    fig.suptitle("SPAN-CPT + IE reference (not bias ground truth)")
    fig.savefig(output / "reference_motion.png", dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), constrained_layout=True)
    for ax, frame, label in zip(axes, [imu, reference], ["IMU", "Reference"]):
        t = relative_seconds(frame.time_ns, origin)
        dt_ms = np.diff(frame.time_ns.to_numpy(dtype=np.int64)).astype(float) / 1e6
        ax.plot(t[1:], dt_ms, lw=.6)
        ax.set(xlabel="Time (s)", ylabel=f"{label} sample interval (ms)")
        ax.grid(alpha=.25)
    fig.suptitle("Timestamp intervals (all samples)")
    fig.savefig(output / "timing.png", dpi=140)
    plt.close(fig)
