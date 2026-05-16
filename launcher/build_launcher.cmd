@echo off
setlocal
cd /d "%~dp0"

if not exist clean_env\Scripts\python.exe (
    py -3.11 -m venv clean_env
)

clean_env\Scripts\python.exe -m pip install --upgrade pip pyinstaller PySide6
clean_env\Scripts\python.exe package_app.py
if exist dist\MangaOCR.exe del /f /q dist\MangaOCR.exe
if exist dist\MangaOCR-Launcher.exe del /f /q dist\MangaOCR-Launcher.exe
clean_env\Scripts\python.exe -m PyInstaller --clean --noconfirm --workpath build --distpath dist launcher.spec

echo.
echo Built: %~dp0dist\MangaOCR.exe
pause
