@echo off
setlocal EnableExtensions

echo.
echo ============================================
echo         SmartEdit Video Editor
echo ============================================
echo.

rem ----- Set up tools -----
set "PYTHON_EXE=C:\msys64\mingw64\bin\python.exe"
set "UCRT_BIN=C:\msys64\mingw64\bin"

rem ----- Verify Python exists -----
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at: %PYTHON_EXE%
    echo Please edit this .bat file and set PYTHON_EXE to your python.exe path.
    pause
    exit /b 1
)

rem ----- Add ucrt64 bin to PATH (required for DLLs) -----
if exist "%UCRT_BIN%" set "PATH=%UCRT_BIN%;%PATH%"


if exist "%BASE%SmartEdit\smartedit-qt\src\launch.py"   set "SRC=%BASE%SmartEdit\smartedit-qt\src"


rem ----- Ensure binary compatibility copies exist -----
if exist "%SRC%\libsmartedit.dll" if not exist "%SRC%\libsmartedit.dll" copy /y "%SRC%\libsmartedit.dll" "%SRC%\libsmartedit.dll" >nul
if exist "%SRC%\libsmartedit-audio.dll" if not exist "%SRC%\libsmartedit-audio.dll" copy /y "%SRC%\libsmartedit-audio.dll" "%SRC%\libsmartedit-audio.dll" >nul
if exist "%SRC%\_smartedit.pyd" if not exist "%SRC%\_smartedit.pyd" copy /y "%SRC%\_smartedit.pyd" "%SRC%\_smartedit.pyd" >nul

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