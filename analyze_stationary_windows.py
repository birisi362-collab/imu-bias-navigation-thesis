"""Uzun duruş adaylarında eşit süreli jiroskop ofseti incelemesi."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from imu_thesis.data import read_imu, read_reference
from imu_thesis.stationary import analyze_stops


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/stationary_windows"))
    parser.add_argument("--window-s", type=float, default=20.)
    parser.add_argument("--edge-s", type=float, default=1.)
    parser.add_argument("--imu-time-column", choices=["field.header.stamp", "%time"], default="field.header.stamp")
    parser.add_argument("--reference-time-offset-s", default="0")
    args = parser.parse_args(argv)
    try:
        imu = read_imu(args.imu, args.imu_time_column)
        reference = read_reference(args.reference, args.reference_time_offset_s)
        motion, report = analyze_stops(imu, reference, args.window_s, args.edge_s)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/"stationary_windows_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        pd.DataFrame(report["inventory"]).to_csv(args.output/"stop_inventory.csv", index=False)
        pd.DataFrame(report["equal_windows"]).to_csv(args.output/"equal_window_statistics.csv", index=False)
        fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
        axes[0].plot(motion.elapsed_s, motion.reference_speed_m_s, color="tab:gray")
        axes[0].set_ylabel("Reference speed\n(m/s)")
        axes[0].set_title("Reference-assisted stop selection; fixed equal windows")
        for item in report["inventory"]:
            if item["status"] == "stationary_candidate":
                axes[0].axvspan(item["start_s"], item["end_s"], color="tab:green", alpha=.2)
        for item in report["equal_windows"]:
            start, duration = item["start_s"], item["duration_s"]
            axes[0].axvspan(start, start+duration, color="tab:blue", alpha=.25)
        for i, axis in enumerate("xyz", start=1):
            for j, item in enumerate(report["equal_windows"]):
                start, duration = item["start_s"], item["duration_s"]
                axes[i].scatter(start+duration/2, np.rad2deg(item[f"offset_candidate_{axis}_rad_s"]),
                                color="tab:blue", marker="o", label="Whole window" if j==0 else None)
                axes[i].scatter([start+duration/4, start+3*duration/4],
                                np.rad2deg([item[f"first_half_offset_{axis}_rad_s"],
                                            item[f"second_half_offset_{axis}_rad_s"]]),
                                color="tab:orange", marker="x", label="Two halves" if j==0 else None)
            axes[i].set_ylabel(f"{axis} offset candidate\n(deg/s)")
            if report["equal_windows"]:
                axes[i].legend(loc="best")
        for ax in axes:
            ax.grid(alpha=.3)
        axes[-1].set_xlabel("Time since first IMU sample (s); points are not bias truth")
        fig.tight_layout()
        fig.savefig(args.output/"stationary_windows.png", dpi=150)
        plt.close(fig)
        print(f"Duruş adayı: {report['candidate_count']} | Toplam: {report['total_candidate_span_s']:.1f} s")
        print(f"Eşit {args.window_s:g} saniyelik pencere: {len(report['equal_windows'])}")
        for item in report["equal_windows"]:
            offset = [round(float(np.rad2deg(item[f"offset_candidate_{a}_rad_s"])), 6) for a in "xyz"]
            halves = [round(float(np.rad2deg(item[f"second_minus_first_{a}_rad_s"])), 6) for a in "xyz"]
            print(f"Duruş {item['stop_id']}, t={item['start_s']:.3f} s: {offset} deg/s; ikinci-ilk yarı: {halves}")
        print(f"Çıktılar: {args.output.resolve()}")
        print("Bunlar referans destekli ofset adaylarıdır; fiziksel bias veya çevrim içi öğrenme sonucu değildir.")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
