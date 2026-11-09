"""Eski/güncel ve kısa/uzun duruş ortalamalarının kontrollü karşılaştırması."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from imu_thesis.calibration_factors import compare_calibration_factors
from imu_thesis.data import read_imu, read_reference


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/calibration_factors"))
    parser.add_argument("--duration-s", type=float, default=60.)
    parser.add_argument("--imu-time-column", choices=["field.header.stamp", "%time"], default="field.header.stamp")
    parser.add_argument("--reference-time-offset-s", default="0")
    args = parser.parse_args(argv)
    try:
        imu = read_imu(args.imu, args.imu_time_column)
        reference = read_reference(args.reference, args.reference_time_offset_s)
        table, report = compare_calibration_factors(imu, reference, args.duration_s)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/"calibration_factors_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        table.to_csv(args.output/"calibration_factors_at_reference_epochs.csv", index=False)
        experiments = [e for e in report["experiments"] if e["status"]=="evaluated"]
        if not experiments:
            raise ValueError("Değerlendirilebilen sonraki duruş yok; nedenler JSON raporunda.")
        fig, axes = plt.subplots(len(experiments), 2, figsize=(12, 3.3*len(experiments)),
                                 squeeze=False, sharex=True, sharey="row")
        summary = []
        for i, e in enumerate(experiments):
            part = table.loc[table.stop_id==e["stop_id"]]
            start_s = (e["evaluation"]["start_time_ns"]-int(imu.time_ns.iloc[0]))/1e9
            row = {"stop_id": e["stop_id"], "evaluation_start_s": start_s}
            for j, length in enumerate(["short", "long"]):
                for age, color in [("old", "tab:blue"), ("recent", "tab:orange")]:
                    name = f"{age}_{length}"
                    axes[i,j].plot(part.elapsed_s, part[f"{name}_angle_difference_deg"],
                                   color=color, label="First long stop" if age=="old" else "Recent stop")
                    metrics = e["evaluation"]["variants"][name]
                    row[f"{name}_final_deg"] = metrics["final_angle_difference_deg"]
                    row[f"{name}_rms_deg"] = metrics["rms_angle_difference_deg"]
                duration = report["short_s"] if length=="short" else report["long_s"]
                axes[i,j].set_title(f"Stop {e['stop_id']}; start={start_s:.3f} s; {duration:g} s means")
                axes[i,j].set_ylabel("Rotation difference (deg)")
                axes[i,j].grid(alpha=.3)
                axes[i,j].legend(fontsize=8)
            summary.append(row)
            print(f"Duruş {e['stop_id']}: " + "; ".join(
                f"{name}={row[f'{name}_final_deg']:.4f}° (RMS {row[f'{name}_rms_deg']:.4f}°)"
                for name in ["old_short", "old_long", "recent_short", "recent_long"]))
        for ax in axes[-1]:
            ax.set_xlabel("Time since identical one-time initialization (s)")
        fig.suptitle("Calibration age vs averaging length — reference-assisted offline diagnostic")
        fig.tight_layout(rect=[0,0,1,.97])
        fig.savefig(args.output/"calibration_factors_comparison.png", dpi=150)
        plt.close(fig)
        pd.DataFrame(summary).to_csv(args.output/"calibration_factors_summary.csv", index=False)
        print(f"Sabit eski kalibrasyon: ilk uzun duruş, ID {report['baseline_stop_id']}")
        print(f"Çıktılar: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
