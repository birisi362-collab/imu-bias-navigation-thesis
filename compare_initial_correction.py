"""Başlangıç duruş adayı ortalamasının sonraki yönelim hesabına etkisi."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from imu_thesis.audit import audit_data
from imu_thesis.data import read_imu, read_reference
from imu_thesis.initial_correction import compare_initial_correction


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/initial_correction"))
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
        table, report = compare_initial_correction(imu, reference, args.calibration_duration_s,
                                                   args.duration_s, args.max_imu_gap_ms/1000)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s,
                            "requested_evaluation_duration_s": args.duration_s,
                            "max_imu_gap_ms": args.max_imu_gap_ms}
        args.output.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.output / "initial_correction_at_reference_epochs.csv", index=False)
        (args.output / "initial_correction_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        axes[0].plot(table.elapsed_s, table.raw_angle_difference_deg, label="Raw gyro", color="tab:gray")
        axes[0].plot(table.elapsed_s, table.fixed_angle_difference_deg, label="Fixed initial offset", color="tab:blue")
        axes[0].set_ylabel("Rotation difference (deg)")
        axes[0].set_title("Same evaluation interval and initialization — diagnostic only")
        axes[0].legend()
        for axis in "xyz":
            axes[1].plot(table.elapsed_s, table[f"fixed_difference_rotvec_{axis}_deg"], label=axis)
        axes[1].set_ylabel("Fixed-offset difference vector (deg)")
        axes[1].set_xlabel("Time since evaluation initialization, after calibration (s)")
        axes[1].legend(title="Reference body axes")
        for ax in axes:
            ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(args.output / "initial_correction_comparison.png", dpi=150)
        plt.close(fig)
        print(f"Başlangıç düzeltmesi: {report['calibration']['gyro_offset_xyz_rad_s']} rad/s")
        print(f"Değerlendirme süresi: {report['raw']['duration_s']:.1f} s")
        print(f"Ham son fark: {report['raw']['final_angle_difference_deg']:.4f} derece")
        print(f"Sabit düzeltmeli son fark: {report['fixed_initial_offset']['final_angle_difference_deg']:.4f} derece")
        print(f"Çıktılar: {args.output.resolve()}")
        print("Bu bir başlangıç düzeltmesi tanısıdır; saf bias doğruluğu veya öğrenme sonucu değildir.")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
