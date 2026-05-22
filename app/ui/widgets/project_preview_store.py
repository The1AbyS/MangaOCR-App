import os
import shutil
from pathlib import Path

from ...core.utils import natural_key


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
PREVIEWS_DIR = Path.home() / ".mangaocr_previews"


def preview_key(project_path: str) -> str:
    import hashlib
    return hashlib.md5(str(Path(project_path).resolve()).encode()).hexdigest()


def custom_preview_path(project_path: str, ext: str = "") -> Path:
    return PREVIEWS_DIR / (preview_key(project_path) + ext)


def find_custom_preview(project_path: str) -> str | None:
    if not PREVIEWS_DIR.exists():
        return None
    key = preview_key(project_path)
    for ext in IMAGE_EXTENSIONS:
        candidate = PREVIEWS_DIR / (key + ext)
        if candidate.exists():
            return str(candidate)
    return None


def find_preview(folder: str) -> str | None:
    custom = find_custom_preview(folder)
    if custom:
        return custom

    try:
        for file in sorted(os.listdir(folder), key=natural_key):
            if file.lower().endswith(IMAGE_EXTENSIONS):
                return os.path.join(folder, file)
    except OSError:
        pass
    return None


def project_sort_key(name: str):
    stripped = name.strip()
    if stripped.isdigit():
        return (0, -int(stripped), natural_key(name))
    return (1, natural_key(name))


def set_custom_preview(project_path: str, image_path: str) -> bool:
    ext = Path(image_path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        return False
    try:
        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        remove_custom_preview(project_path)
        dest = custom_preview_path(project_path, ext)
        shutil.copy2(image_path, dest)
        return True
    except OSError:
        return False


def remove_custom_preview(project_path: str) -> bool:
    key = preview_key(project_path)
    removed = False
    for ext in IMAGE_EXTENSIONS:
        candidate = PREVIEWS_DIR / (key + ext)
        try:
            candidate.unlink()
            removed = True
        except FileNotFoundError:
            pass
        except OSError:
            pass
    return removed


def build_project_list(folder: str) -> list[dict]:
    projects = []
    try:
        for name in sorted(os.listdir(folder), key=project_sort_key):
            full_path = os.path.join(folder, name)

            if not os.path.isdir(full_path):
                continue

            try:
                items = os.listdir(full_path)
            except OSError:
                items = []

            image_count = sum(
                1 for file in items
                if file.lower().endswith(IMAGE_EXTENSIONS)
            )

            folder_count = sum(
                1 for file in items
                if os.path.isdir(os.path.join(full_path, file))
            )

            projects.append({
                "name": name,
                "path": full_path,
                "preview": find_preview(full_path),
                "image_count": image_count,
                "folder_count": folder_count,
            })

    except OSError as e:
        raise RuntimeError(f"РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕС‡РёС‚Р°С‚СЊ РїР°РїРєСѓ: {e}") from e

    return projects
