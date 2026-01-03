@echo off
setlocal
chcp 65001 >nul

set REPO_URL=https://github.com/The1AbyS/MangaOCR-App
set REPO_DIR=%~dp0
set BRANCH=main
set PYTHON=python
set REQ=PySide6 opencv-python numpy pillow manga-ocr loguru scikit-image ultralytics python-docx requests beautifulsoup4 gdown
set FIRST_RUN_FLAG=%REPO_DIR%requirements\first_run.flag

set MODEL_DIR=%REPO_DIR%models
set MODEL_FILE=%MODEL_DIR%\yolo_m.pt
set MODEL_OCR=%MODEL_DIR%\model_manga_ocr
set DRIVE_OCR_URL=https://drive.google.com/drive/folders/1m9sQIvEGom-2BP4iwqdF8wiFCyfLfi03
set DRIVE_FILE_URL=https://drive.google.com/uc?id=1mEM5KFc-I1HAA3YkK9gapvxYcphaCzXG

echo Проверка обновлений...
pushd "%REPO_DIR%"
git fetch
git checkout %BRANCH%
git pull origin %BRANCH%
popd

if not exist "%FIRST_RUN_FLAG%" (

    echo Проверка зависимостей...
    for %%p in (%REQ%) do (
        %PYTHON% -m pip show %%p >nul 2>&1
        if errorlevel 1 (
            echo Не найден %%p — устанавливаю...
            %PYTHON% -m pip install %%p
        ) else (
            echo OK: %%p
        )
    )

    %PYTHON% -c "import torch" >nul 2>&1
    if %errorlevel%==0 (
        echo OK: torch
    ) else (
        call :CHOOSE_TORCH
    )
)

if not exist "%MODEL_FILE%" (
    echo Файл yolo_m.pt не найден. Скачиваю в %MODEL_DIR%...
    call %PYTHON% -m gdown "%DRIVE_FILE_URL%" -O "%MODEL_FILE%"
)
if not exist "%MODEL_FILE%" (
    echo Ошибка: yolo_m.pt не был скачан!
    pause
    exit /b
)

if not exist "%MODEL_OCR%" (
    echo Папка model_manga_ocr не найдена. Скачиваю всю папку в %MODEL_DIR%...
    mkdir "%MODEL_DIR%\model_manga_ocr"
    call %PYTHON% -m gdown "%DRIVE_OCR_URL%" --folder -O "%MODEL_DIR%\model_manga_ocr"
)
if not exist "%MODEL_OCR%" (
    echo Ошибка: model_manga_ocr не была скачана!
    pause
    exit /b
)

%PYTHON% -c "import torch" >nul 2>&1
if %errorlevel%==0 goto CONTINUE_TORCH

echo Torch не найден, нужно установить.
goto CHOOSE_TORCH

:CHOOSE_TORCH
echo.
echo Установка PyTorch
echo 1) GPU (Минимальные требования: Nvidia GTX 780/780 Ti, GTX 900 серии, или новее. Видеокарты AMD не поддерживаются)
echo 2) CPU 
set /p CHOICE=Введите 1 или 2: 
if "%CHOICE%"=="1" goto TORCH_GPU
if "%CHOICE%"=="2" goto TORCH_CPU
echo Неверный выбор.
pause
exit /b

:TORCH_GPU
echo Устанавливаю PyTorch (GPU)
%PYTHON% -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
nvcc --version >nul 2>&1
if errorlevel 1 (
    echo CUDA Toolkit не установлен, переход по ссылке...
    start https://developer.nvidia.com/cuda-11-8-0-download-archive
)
goto CREATE_FLAG

:TORCH_CPU
echo Устанавливаю PyTorch (CPU)
%PYTHON% -m pip install torch torchvision torchaudio
goto CREATE_FLAG

:CONTINUE_TORCH
goto CREATE_FLAG

:CREATE_FLAG
echo > "%FIRST_RUN_FLAG%"
echo Первый запуск завершен. Флаг создан.

:RUN
echo.
echo Запуск MangaOCR App...
"%PYTHON%" run.py

endlocal
