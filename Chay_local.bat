@echo off
setlocal EnableExtensions
chcp 65001 >nul

rem Run from the repository root, regardless of the caller's current directory.
cd /d "%~dp0"
set "PROJECT_DIR=%~dp0AI_PROJECT"
set "VENV_DIR=%~dp0venv"
set "APP_FILE=%PROJECT_DIR%\APP\frontend\app.py"
set "REQUIREMENTS=%PROJECT_DIR%\requirements.txt"
set "ENV_FILE=%PROJECT_DIR%\.env"
set "ENV_TEMPLATE=%PROJECT_DIR%\.env.example"

if not exist "%APP_FILE%" (
    echo [LOI] Khong tim thay file ung dung:
    echo       "%APP_FILE%"
    pause
    exit /b 1
)

if not exist "%REQUIREMENTS%" (
    echo [LOI] Khong tim thay file requirements.txt.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Chua co moi truong Python rieng. Dang tao venv...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv "%VENV_DIR%"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo [LOI] May chua cai Python 3 hoac Python chua duoc them vao PATH.
            echo Hay cai Python 3, chon tuy chon Add Python to PATH, roi bam lai file nay.
            pause
            exit /b 1
        )
        python -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (
        echo [LOI] Khong tao duoc venv. Hay kiem tra cai dat Python.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Da tim thay venv.
)

if not exist "%ENV_FILE%" (
    if exist "%ENV_TEMPLATE%" (
        copy /Y "%ENV_TEMPLATE%" "%ENV_FILE%" >nul
        echo [2/4] Da tao AI_PROJECT\.env tu file mau.
        echo Hay mo file AI_PROJECT\.env va dien thong tin MySQL, Gemini truoc khi chay.
        echo MySQL phai dang chay va DB_HOST phai tro den may chu ma ban truy cap duoc.
        pause
        exit /b 1
    ) else (
        echo [LOI] Thieu AI_PROJECT\.env va AI_PROJECT\.env.example.
        pause
        exit /b 1
    )
)

echo [2/4] Dang kiem tra va cai cac thu vien...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"
if errorlevel 1 (
    echo [LOI] Cai thu vien that bai. Hay kiem tra ket noi Internet va thu lai.
    pause
    exit /b 1
)

echo [3/4] Dang khoi dong Streamlit tren may nay...
echo Khi ung dung mo trong trinh duyet, giu cua so nay mo.
echo Nhan Ctrl+C tai day de dung server.
"%VENV_DIR%\Scripts\python.exe" -m streamlit run "%APP_FILE%" --server.address 127.0.0.1

if errorlevel 1 (
    echo [LOI] Streamlit da dung do gap loi. Hay doc thong bao phia tren.
    pause
)
endlocal