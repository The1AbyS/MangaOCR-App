# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

spec_dir = Path(SPECPATH)
project_dir = spec_dir.parent
app_icon = project_dir / "app" / "ui" / "icons" / "Mocr.ico"
app_zip = spec_dir / "build_assets" / "app_source.zip"
manifest = spec_dir / "build_assets" / "manifest.json"

a = Analysis(
    [str(spec_dir / "launcher.py")],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        (str(app_icon), "app/ui/icons"),
        (str(app_zip), "launcher_payload"),
        (str(manifest), "launcher_payload"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MangaOCR",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(app_icon),
)
