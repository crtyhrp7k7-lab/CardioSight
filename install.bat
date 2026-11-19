@echo off
rem CardioSight Shunt Simulator - Windows installer.
rem Copies the app to %LOCALAPPDATA%\Programs, creates a private Python environment with
rem the plotting packages, runs a quick self-test and adds Desktop + Start Menu shortcuts.
rem No administrator rights needed. Re-running it updates an existing installation.
setlocal EnableExtensions
title CardioSight Shunt Simulator - installer
set "SRC=%~dp0"
set "DEST=%LOCALAPPDATA%\Programs\CardioSight Shunt Simulator"

echo.
echo  CardioSight Shunt Simulator - installer
echo  ========================================
echo.

if not exist "%SRC%launcher.py" (
    echo  The program files were not found next to install.bat.
    echo  Please right-click the zip file, choose "Extract All...", then run
    echo  install.bat from the extracted folder.
    goto :fail
)

rem ---- 1. Find Python 3.8+ with Tkinter -------------------------------------------
call :findpy
if defined PY goto :havepy
echo  Python 3 was not found. Trying to install it with winget...
where winget >nul 2>nul
if errorlevel 1 goto :nopython
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
set "NEWPY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%NEWPY%" set PY="%NEWPY%"
if not defined PY call :findpy
if not defined PY goto :nopython
:havepy
echo  Using Python:
%PY% -c "import sys; print('   ', sys.executable, sys.version.split()[0])"

rem ---- 2. Copy the program files -----------------------------------------------------
echo.
echo  [1/4] Copying files to "%DEST%"
if /i "%SRC%"=="%DEST%\" goto :copied
robocopy "%SRC%." "%DEST%" /E /XD .venv __pycache__ results .git dist /XF *.zip /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo  Copy failed.
    goto :fail
)
:copied

rem ---- 3. Private Python environment + packages ------------------------------------
echo  [2/4] Creating the Python environment and installing packages (needs internet)...
set "VPY=%DEST%\.venv\Scripts\python.exe"
if not exist "%VPY%" (
    %PY% -m venv "%DEST%\.venv"
    if errorlevel 1 (
        echo  Could not create the Python environment.
        goto :fail
    )
)
"%VPY%" -m pip install --disable-pip-version-check -q -r "%DEST%\requirements.txt"
if errorlevel 1 (
    echo  Package installation failed. Check the internet connection and run install.bat again.
    goto :fail
)

rem ---- 4. Self-test -------------------------------------------------------------------
echo  [3/4] Self-test (about 15-30 s)...
pushd "%DEST%"
"%VPY%" -c "import tkinter, matplotlib, launcher, scenario" >nul 2>nul
if errorlevel 1 (
    popd
    echo  The program could not be loaded. Details:
    "%VPY%" -c "import tkinter, matplotlib, launcher, scenario"
    goto :fail
)
"%VPY%" test_baseline.py >nul 2>nul
if errorlevel 1 (
    echo  WARNING: the baseline self-test did not pass. The app will still be installed;
    echo  please tell the sender. To see details run:  "%VPY%" "%DEST%\test_baseline.py"
) else (
    echo         passed.
)
popd

rem ---- 5. Shortcuts -----------------------------------------------------------------
echo  [4/4] Creating Desktop and Start Menu shortcuts...
"%VPY%" "%DEST%\create_shortcut.py"
if errorlevel 1 goto :fail

echo.
echo  Done. Start "CardioSight Shunt Simulator" from the Desktop or the Start Menu.
echo  To remove it later, run uninstall.bat in:
echo    %DEST%
echo  You can now delete the zip file and the extracted folder.
echo.
pause
exit /b 0

rem ---- helpers ------------------------------------------------------------------------
:findpy
set "PY="
py -3 -c "import sys, tkinter; sys.exit(sys.version_info < (3, 8))" >nul 2>nul
if not errorlevel 1 ( set "PY=py -3" & exit /b 0 )
python -c "import sys, tkinter; sys.exit(sys.version_info < (3, 8))" >nul 2>nul
if not errorlevel 1 ( set "PY=python" & exit /b 0 )
exit /b 0

:nopython
echo.
echo  Python 3 (with Tkinter) is required but could not be found or installed.
echo  1. Download Python from https://www.python.org/downloads/windows/
echo  2. Run the installer with the default options ("tcl/tk and IDLE" included).
echo  3. Run install.bat again.
:fail
echo.
echo  Installation did not complete.
pause
exit /b 1
