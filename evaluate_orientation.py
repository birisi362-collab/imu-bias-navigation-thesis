"""Quaternion ile ham jiroskop yönelim tanısı (varsayılan ilk 60 saniye)."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from imu_thesis.audit import audit_data
from imu_thesis.data import read_imu, read_reference
from imu_thesis.orientation import orientation_diagnostic


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/orientation"))
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
        table, report = orientation_diagnostic(imu, reference, args.duration_s, args.max_imu_gap_ms/1000)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s,
                            "requested_duration_s": args.duration_s,
                            "max_imu_gap_ms": args.max_imu_gap_ms}
        args.output.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.output / "orientation_at_reference_epochs.csv", index=False)
        (args.output / "orientation_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        axes[0].plot(table.elapsed_s, table.angle_difference_deg, color="black")
        axes[0].set_ylabel("Rotation difference (deg)")
        axes[0].set_title("Raw gyro quaternion integration — diagnostic only")
        for axis in "xyz":
            axes[1].plot(table.elapsed_s, table[f"difference_rotvec_{axis}_deg"], label=axis)
        axes[1].set_ylabel("Difference vector (deg)")
        axes[1].set_xlabel("Time since one-time reference initialization (s)")
        axes[1].legend(title="Reference body axes")
        for ax in axes:
            ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(args.output / "orientation_difference.png", dpi=150)
        plt.close(fig)
        print(f"Süre: {report['duration_s']:.1f} s | Referans anı: {len(table)}")
        print(f"Son yönelim farkı: {report['final_angle_difference_deg']:.4f} derece")
        print(f"Çıktılar: {args.output.resolve()}")
        print("Bu sonuç bias doğruluğu veya GNSS/INS performansı değildir; rapordaki sınırları okuyun.")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
