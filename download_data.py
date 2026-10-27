"""Download only the Medium-Urban-1 IMU CSV and reference TXT (not the ROS bag)."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

SOURCES = {
    "xsense_imu_medium_urban1.csv": "https://www.dropbox.com/s/2rh1rs15ihpf63u/xsense_imu_medium_urban1.csv?dl=1",
    "UrbanNav_TST_GT_raw.txt": "https://www.dropbox.com/s/twsvwftucoytfpc/UrbanNav_TST_GT_raw.txt?dl=1",
}


def download(url, destination: Path, force=False):
    if destination.exists() and not force:
        raise FileExistsError(f"Dosya zaten var: {destination}. Yenilemek için --force kullanın.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "imu-bias-navigation-thesis/0.1", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 200 or response.headers.get("Content-Range"):
                raise ValueError("Sunucu tam dosya yerine kısmi içerik döndürdü; dosya kaydedilmedi. Kaynak bağlantıdan elle indirin.")
            if "text/html" in response.headers.get("Content-Type", "").lower():
                raise ValueError("Veri yerine HTML sayfası döndü; kaynak bağlantıyı kontrol edin.")
            size, digest = 0, hashlib.sha256()
            expected = response.headers.get("Content-Length")
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".part", delete=False) as handle:
                temp = Path(handle.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    if size == 0 and (b"<html" in chunk[:512].lower() or b"<!doctype html" in chunk[:512].lower()):
                        raise ValueError("İndirilen içerik veri dosyası değil.")
                    size += len(chunk)
                    if size > 256 * 1024 * 1024:
                        raise ValueError("Bu indirme için 256 MiB boyut sınırı aşıldı.")
                    handle.write(chunk)
                    digest.update(chunk)
            if size == 0 or (expected and size != int(expected)):
                raise ValueError("Dosya boş veya indirme eksik.")
        temp.replace(destination)
        return {"filename": destination.name, "url": url, "bytes": size, "sha256": digest.hexdigest(),
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat()}
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/medium"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = []
    try:
        for name, url in SOURCES.items():
            print(f"İndiriliyor: {name}", flush=True)
            manifest.append(download(url, args.output / name, args.force))
            (args.output / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"Tamam: {manifest[-1]['bytes'] / 1e6:.2f} MB", flush=True)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"İndirme tamamlanamadı: {exc}\nElle indirme seçenekleri README.md içinde.\n")


if __name__ == "__main__":
    main()
