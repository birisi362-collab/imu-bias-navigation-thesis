"""Geçmiş duruştaki sabit düzeltmenin sonraki hareket aralığına katkısı."""

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
from imu_thesis.post_stop import compare_post_stop


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/medium/post_stop"))
    parser.add_argument("--duration-s", type=float, default=60.)
    parser.add_argument("--imu-time-column", choices=["field.header.stamp", "%time"], default="field.header.stamp")
    parser.add_argument("--reference-time-offset-s", default="0")
    args = parser.parse_args(argv)
    try:
        imu = read_imu(args.imu, args.imu_time_column)
        reference = read_reference(args.reference, args.reference_time_offset_s)
        table, report = compare_post_stop(imu, reference, args.duration_s)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/"post_stop_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        table.to_csv(args.output/"post_stop_at_reference_epochs.csv", index=False)
        experiments = [e for e in report["experiments"] if e["status"] == "evaluated"]
        for e in report["experiments"]:
            if e["status"] != "evaluated":
                print(f"Duruş {e['stop_id']} atlandı: {e['reason']}")
        if not experiments:
            raise ValueError("Tam süreli değerlendirilebilir deney yok; nedenler JSON raporunda.")
        labels = {"no_offset": "No sensor offset correction (+ Earth rate)",
                  "initial": "Initial 5 s offset (+ Earth rate)",
                  "recent": "Recent stop 20 s offset (+ Earth rate)"}
        colors = {"no_offset": "tab:gray", "initial": "tab:blue", "recent": "tab:orange"}
        fig, axes = plt.subplots(len(experiments), 2, figsize=(13, 3.2*len(experiments)),
                                 squeeze=False, sharex=True)
        summary = []
        for i, e in enumerate(experiments):
            part = table.loc[table.stop_id == e["stop_id"]]
            start_s = (e["evaluation"]["start_time_ns"]-int(imu.time_ns.iloc[0]))/1e9
            row = {"stop_id": e["stop_id"], "evaluation_start_s": start_s}
            for name, label in labels.items():
                axes[i, 0].plot(part.elapsed_s, part[f"{name}_angle_difference_deg"], label=label, color=colors[name])
                if name != "no_offset":
                    axes[i, 1].plot(part.elapsed_s, part[f"{name}_angle_difference_deg"], label=label, color=colors[name])
                values = e["evaluation"]["variants"][name]
                row[f"{name}_final_deg"] = values["final_angle_difference_deg"]
                row[f"{name}_rms_deg"] = values["rms_angle_difference_deg"]
            summary.append(row)
            axes[i, 0].set_title(f"After stop {e['stop_id']}; start t={start_s:.3f} s")
            axes[i, 1].set_title("Corrected curves only")
            for ax in axes[i]:
                ax.set_ylabel("Rotation difference (deg)")
                ax.grid(alpha=.3)
                ax.legend(fontsize=8)
            print(f"Duruş {e['stop_id']}, başlangıç {start_s:.3f} s: son fark "
                  f"ofsetsiz={row['no_offset_final_deg']:.4f}°, ilk={row['initial_final_deg']:.4f}°, "
                  f"güncel={row['recent_final_deg']:.4f}°; RMS ilk={row['initial_rms_deg']:.4f}°, "
                  f"güncel={row['recent_rms_deg']:.4f}°")
        for ax in axes[-1]:
            ax.set_xlabel("Time since common one-time reference initialization (s)")
        fig.suptitle("Frozen offsets after reference-assisted stops — offline diagnostic only", fontsize=12)
        fig.tight_layout(rect=[0, 0, 1, .97])
        fig.savefig(args.output/"post_stop_comparison.png", dpi=150)
        plt.close(fig)
        pd.DataFrame(summary).to_csv(args.output/"post_stop_summary.csv", index=False)
        print(f"Çıktılar: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
