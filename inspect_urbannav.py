"""Step 01: read, audit, and visualize one UrbanNav IMU/reference pair."""

import argparse
import json
from pathlib import Path
import sys

from imu_thesis.audit import audit_data
from imu_thesis.data import read_imu, read_reference
from imu_thesis.plots import make_plots


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imu", type=Path, required=True, help="Xsens IMU CSV yolu")
    parser.add_argument("--reference", type=Path, required=True, help="SPAN-CPT + IE metin yolu")
    parser.add_argument("--output", type=Path, default=Path("outputs/medium"))
    parser.add_argument("--imu-time-column", choices=["field.header.stamp", "%time"], default="field.header.stamp")
    parser.add_argument("--reference-time-offset-s", default="0", help="Yalnız doğrulanmış sabit saat farkı için; varsayılan 0")
    parser.add_argument("--match-tolerance-ms", type=float, default=10)
    args = parser.parse_args(argv)
    try:
        imu = read_imu(args.imu, args.imu_time_column)
        reference = read_reference(args.reference, args.reference_time_offset_s)
        report, paired = audit_data(imu, reference, args.match_tolerance_ms / 1000)
        report["inputs"] = {"imu": str(args.imu.resolve()), "reference": str(args.reference.resolve()),
                            "imu_time_column": args.imu_time_column,
                            "reference_time_offset_s": args.reference_time_offset_s}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        print(f"IMU: {len(imu):,} örnek | Referans: {len(reference):,} örnek")
        if report["errors"]:
            for error in report["errors"]:
                print(f"HATA: {error}", file=sys.stderr)
            print(f"Kontrol raporu: {args.output / 'quality_report.json'}")
            return 2
        paired.to_csv(args.output / "reference_epochs_with_nearest_imu.csv", index=False)
        make_plots(imu, reference, args.output)
        print(f"IMU medyan frekansı: {report['imu']['median_rate_hz']:.2f} Hz")
        print(f"Ortak zaman kapsamı: {report['overlap']['duration_s']:.2f} s")
        print(f"Çıktılar: {args.output.resolve()}")
        print("Bu aşama veri incelemesidir; kalibrasyon, mekanizasyon veya model eğitimi yapılmadı.")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
