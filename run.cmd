@echo off
setlocal
chcp 65001 >nul

set REPO_URL=https://github.com/The1AbyS/MangaOCR-App
set REPO_DIR=%~dp0
set BRANCH=main
set PYTHON=python

set REQ=PySide6 PyQtWebEngine opencv-python numpy pillow manga-ocr loguru scikit-image ultralytics python-docx requests beautifulsoup4

set FIRST_RUN_FLAG=%REPO_DIR%requirements\first_run.flag


echo Проверка обновлений...

pushd "%REPO_DIR%"
git fetch
git checkout %BRANCH%
git pull origin %BRANCH%
popd


echo.
echo Проверка зависимостей...

if not exist "%FIRST_RUN_FLAG%" (

    echo Первый запуск — проверяю библиотеки...

    for %%p in (%REQ%) do (
        %PYTHON% -c "import %%p" 2>nul
        if errorlevel 1 (
            echo Не найдена %%p — устанавливаю...
            %PYTHON% -m pip install %%p
        ) else (
            echo OK: %%p
        )
    )

    %PYTHON% -c "import torch" 2>nul
    if errorlevel 1 goto CHOOSE_TORCH

    echo Torch уже установлен.
    goto CREATE_FLAG
)


goto RUN


:CHOOSE_TORCH
echo.
echo Установка PyTorch
echo 1) GPU (CUDA)
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
goto CREATE_FLAG


:TORCH_CPU
echo Устанавливаю PyTorch (CPU)
%PYTHON% -m pip install torch torchvision torchaudio
goto CREATE_FLAG


:CREATE_FLAG
echo > "%FIRST_RUN_FLAG%"
echo Файл first_run.flag создан.

:RUN
echo.
echo Запуск MangaOCR App...

"%PYTHON%" run.py

endlocal
