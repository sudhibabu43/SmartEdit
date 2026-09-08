@echo off
setlocal EnableExtensions

echo.
echo ============================================
echo         SmartEdit Video Editor
echo ============================================
echo.

rem ----- Set up tools -----
set "PYTHON_EXE=C:\Python313\python.exe"
set "UCRT_BIN=C:\msys64\ucrt64\bin"

rem ----- Verify Python exists -----
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at: %PYTHON_EXE%
    echo Please edit this .bat file and set PYTHON_EXE to your python.exe path.
    pause
    exit /b 1
)

rem ----- Add ucrt64 bin to PATH (required for DLLs) -----
if exist "%UCRT_BIN%" set "PATH=%UCRT_BIN%;%PATH%"

rem ----- Auto-detect correct SmartEdit source folder -----
rem   Works both BEFORE and AFTER top-level folder rename!
set "BASE=%~dp0"
set "SRC="
if exist "%BASE%OpenShot\smartedit-qt\src\launch.py"    set "SRC=%BASE%OpenShot\smartedit-qt\src"
if exist "%BASE%SmartEdit\smartedit-qt\src\launch.py"   set "SRC=%BASE%SmartEdit\smartedit-qt\src"

if "%SRC%"=="" (
    echo [ERROR] Could not find smartedit-qt\src\launch.py.
    echo.
    echo Tried these paths:
    echo   - %%BASE%%OpenShot\smartedit-qt\src\launch.py
    echo   - %%BASE%%SmartEdit\smartedit-qt\src\launch.py
    echo.
    echo BASE = %BASE%
    pause
    exit /b 2
)

echo [OK] Using source folder: %SRC%
echo [OK] Python: %PYTHON_EXE%
echo.

rem ----- Ensure binary compatibility copies exist -----
if exist "%SRC%\libsmartedit.dll" if not exist "%SRC%\libopenshot.dll" copy /y "%SRC%\libsmartedit.dll" "%SRC%\libopenshot.dll" >nul
if exist "%SRC%\libsmartedit-audio.dll" if not exist "%SRC%\libopenshot-audio.dll" copy /y "%SRC%\libsmartedit-audio.dll" "%SRC%\libopenshot-audio.dll" >nul
if exist "%SRC%\_smartedit.pyd" if not exist "%SRC%\_openshot.pyd" copy /y "%SRC%\_smartedit.pyd" "%SRC%\_openshot.pyd" >nul

echo Starting SmartEdit...
echo.

rem ----- Run the app -----
cd /d "%SRC%"
"%PYTHON_EXE%" "launch.py" %*

rem ----- If it crashed, show error -----
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo [SmartEdit exited with code %EXITCODE%]
    echo.
    pause
)

endlocal