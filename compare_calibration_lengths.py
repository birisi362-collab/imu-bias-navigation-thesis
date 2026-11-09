"""İlk 3/5/10 saniyenin sabit düzeltmelerini aynı sonraki aralıkta karşılaştır."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from imu_thesis.audit import audit_data
from imu_thesis.calibration_sensitivity import compare_calibration_lengths
from imu_thesis.data import read_imu, read_reference


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/calibration_lengths"))
    parser.add_argument("--calibration-lengths-s", nargs="+", type=float, default=[3., 5., 10.])
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
        table, report = compare_calibration_lengths(imu, reference, args.calibration_lengths_s,
                                                    args.duration_s, args.max_imu_gap_ms/1000)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s,
                            "requested_duration_s": args.duration_s, "max_imu_gap_ms": args.max_imu_gap_ms}
        args.output.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.output/"calibration_lengths_at_reference_epochs.csv", index=False)
        (args.output/"calibration_lengths_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
        axes[0].plot(table.elapsed_s, table.raw_angle_difference_deg, label="Raw gyro", color="tab:gray")
        print(f"Ortak başlangıç (ns): {report['evaluation_start_time_ns']}")
        print(f"Gerçek değerlendirme süresi: {report['raw']['duration_s']} s")
        print(f"Ham son fark: {report['raw']['final_angle_difference_deg']:.6f} derece")
        for name, item in report["variants"].items():
            length = item["calibration_duration_s"]
            if item["status"] == "rejected":
                print(f"{length:g} s REDDEDİLDİ: {item['reason']}")
                continue
            for ax in axes:
                ax.plot(table.elapsed_s, table[f"{name}_angle_difference_deg"], label=f"Initial {length:g} s mean")
            print(f"{length:g} s ortalaması: {item['calibration']['gyro_offset_xyz_rad_s']} rad/s")
            print(f"{length:g} s düzeltmesi son fark: {item['evaluation']['final_angle_difference_deg']:.6f} derece")
        axes[0].set_title("Calibration length sensitivity — same evaluation and initialization")
        axes[1].set_title("Fixed-offset curves only; nested windows, not independent repeats")
        for ax in axes:
            ax.set_ylabel("Rotation difference (deg)")
            if ax.lines:
                ax.legend()
            ax.grid(alpha=.3)
        axes[1].set_xlabel("Time after common evaluation initialization (s)")
        fig.tight_layout()
        fig.savefig(args.output/"calibration_lengths_comparison.png", dpi=150)
        plt.close(fig)
        print(f"Çıktılar: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
