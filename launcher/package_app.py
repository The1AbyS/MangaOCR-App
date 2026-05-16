import json
import os
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent / "build_assets"
ZIP_PATH = OUTPUT_DIR / "app_source.zip"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

EXCLUDED_DIRS = {
    ".git",
    ".ruff_cache",
    "__pycache__",
    "launcher",
    "MangaOCR_downloads",
    "model_manga_ocr",
    "clean_env",
    "build",
    "dist",
}
EXCLUDED_FILE_NAMES = {
    ".gitattributes",
    "first_run.flag",
    "yolo_m.pt",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def git_revision():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def should_include(path):
    relative = path.relative_to(PROJECT_ROOT)
    parts = set(relative.parts)
    if parts & EXCLUDED_DIRS:
        return False
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.is_dir():
        return False
    return True


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    manifest = {
        "bundle_id": bundle_id,
        "git": git_revision(),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            root_path = Path(root)
            dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
            for file_name in files:
                path = root_path / file_name
                if should_include(path):
                    archive.write(path, path.relative_to(PROJECT_ROOT).as_posix())

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Packaged app source: {ZIP_PATH}")
    print(f"Bundle id: {bundle_id}")


if __name__ == "__main__":
    main()
