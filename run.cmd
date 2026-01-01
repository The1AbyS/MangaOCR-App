@echo off
setlocal
chcp 65001 >nul

set REPO_URL=https://github.com/The1AbyS/MangaOCR-App
set REPO_DIR=%~dp0
set BRANCH=Alpha-0-2-0
set PYTHON=python


echo Проверка обновлений...

if not exist "%REPO_DIR%" (
    echo Клонирую ветку %BRANCH%...
    git clone -b %BRANCH% "%REPO_URL%" "%REPO_DIR%"
    if errorlevel 1 (
        echo Ошибка клонирования.
        pause
        exit /b
    )
) else (
    echo Обновляю ветку %BRANCH%...
    pushd "%REPO_DIR%"
    git fetch
    git checkout %BRANCH%
    git pull origin %BRANCH%
    echo Обновление прошло успешно
    popd
)

echo Запуск MangaOCR App...

"%PYTHON%" run.py
popd

endlocal
