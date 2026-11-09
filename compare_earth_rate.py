"""Dünya dönüşünü başlangıç ofsetinden ayıran dört yönelim karşılaştırması."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from imu_thesis.audit import audit_data
from imu_thesis.data import read_imu, read_reference
from imu_thesis.earth_rate import earth_rate_comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/earth_rate"))
    parser.add_argument("--calibration-duration-s", type=float, default=5.)
    parser.add_argument("--duration-s", type=float, default=60.)
    parser.add_argument("--max-imu-gap-ms", type=float, default=20.)
    parser.add_argument("--imu-time-column", choices=["field.header.stamp", "%time"], default="field.header.stamp")
    parser.add_argument("--reference-time-offset-s", default="0")
    args = parser.parse_args(argv)
    try:
        imu = read_imu(args.imu, args.imu_time_column)
        reference = read_reference(args.reference, args.reference_time_offset_s)
        audit, _ = audit_data(imu, reference)
        if audit["errors"]:
            raise ValueError("; ".join(audit["errors"]))
        table, report = earth_rate_comparison(imu, reference, args.calibration_duration_s,
                                                   args.duration_s, args.max_imu_gap_ms/1000)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s,
                            "requested_evaluation_duration_s": args.duration_s,
                            "max_imu_gap_ms": args.max_imu_gap_ms}
        args.output.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.output / "earth_rate_at_reference_epochs.csv", index=False)
        (args.output / "earth_rate_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
        labels = {"raw": "Raw gyro", "fixed": "Empirical fixed offset",
                  "earth_only": "Earth rate only", "fixed_earth": "Earth-separated offset + Earth rate"}
        colors = {"raw": "tab:gray", "fixed": "tab:blue", "earth_only": "tab:green", "fixed_earth": "tab:orange"}
        for name, label in labels.items():
            axes[0].plot(table.elapsed_s, table[f"{name}_angle_difference_deg"], label=label, color=colors[name])
        for name in ("fixed", "fixed_earth"):
            axes[1].plot(table.elapsed_s, table[f"{name}_angle_difference_deg"], label=labels[name], color=colors[name])
        axes[0].set_title("Fixed initial latitude; transport rate omitted — diagnostic only")
        for ax in axes:
            ax.set_ylabel("Rotation difference (deg)")
            ax.grid(alpha=.3)
            ax.legend()
        axes[1].set_xlabel("Time after disjoint calibration (s)")
        fig.tight_layout()
        fig.savefig(args.output / "earth_rate_comparison.png", dpi=150)
        plt.close(fig)
        for name, label in labels.items():
            value = report["variants"][name]["final_angle_difference_deg"]
            print(f"{label}: {value:.6f} derece")
        print(f"Dünya dönüşü süre ölçeği: {report['earth_rotation_scale_deg']:.6f} derece")
        print(f"Çıktılar: {args.output.resolve()}")
        print("Sabit enlem tanısıdır; taşıma hızı yoktur, kalan fark fiziksel bias etiketi değildir.")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
