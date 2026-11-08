"""Download from NASA or its acknowledged PHM mirror; never silently use unofficial copies."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from ml.ingestion.nasa import sha256

SOURCES = {
    "nasa": "https://data.nasa.gov/docs/legacy/IMS.zip",
    "phm": "https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip",
}


def safe_names(names: list[str]) -> None:
    for name in names:
        p = PurePosixPath(name.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts or ":" in name:
            raise ValueError(f"Chemin d'archive non sûr : {name}")


def extract_archive(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            safe_names(z.namelist())
            if any((info.external_attr >> 16) & 0o170000 == 0o120000 for info in z.infolist()):
                raise ValueError("Liens symboliques interdits")
            z.extractall(target)
    elif archive.suffix.lower() == ".7z":
        import py7zr
        with py7zr.SevenZipFile(archive) as z:
            safe_names(z.getnames())
            z.extractall(target)
    elif archive.suffix.lower() == ".rar":
        tool = shutil.which("tar") or shutil.which("bsdtar")
        if not tool:
            raise RuntimeError("RAR : extraire manuellement avec 7-Zip ; aucun logiciel système installé.")
        listing = subprocess.check_output([tool, "-tf", str(archive)], text=True)
        safe_names(listing.splitlines())
        subprocess.run([tool, "-xf", str(archive), "-C", str(target)], check=True)
    else:
        raise ValueError("Archive attendue : .zip, .7z ou .rar")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=SOURCES, default="nasa")
    p.add_argument("--archive", type=Path, default=Path("data/archives/IMS.zip"))
    p.add_argument("--extract", action="store_true")
    p.add_argument("--extract-only", action="store_true")
    p.add_argument("--target", type=Path, default=Path("data/raw/nasa_ims"))
    args = p.parse_args()
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    if not args.extract_only and not args.archive.exists():
        tmp = args.archive.with_suffix(args.archive.suffix + ".part")
        try:
            with urllib.request.urlopen(SOURCES[args.source], timeout=60) as response, tmp.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            if not zipfile.is_zipfile(tmp):
                raise ValueError("La réponse reçue n'est pas une archive ZIP valide")
            tmp.replace(args.archive)
        except Exception:
            print("Téléchargement incomplet : voir docs/datasets.md. Aucune donnée n'a été inventée.")
            raise
    if not args.archive.exists():
        raise FileNotFoundError(args.archive)
    metadata = {"download_url": SOURCES[args.source], "verified_at": datetime.now(timezone.utc).isoformat(),
                "bytes": args.archive.stat().st_size, "sha256": sha256(args.archive)}
    args.archive.with_suffix(".provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)
    if args.extract or args.extract_only:
        extract_archive(args.archive.resolve(), args.target.resolve())
        done: set[Path] = set()
        while True:
            pending = [a for a in args.target.rglob("*")
                       if a.suffix.lower() in {".7z", ".rar", ".zip"} and a not in done]
            if not pending:
                break
            for archive in pending:
                print(f"Extraction : {archive}", flush=True)
                extract_archive(archive.resolve(), args.target.resolve())
                done.add(archive)


if __name__ == "__main__":
    main()
