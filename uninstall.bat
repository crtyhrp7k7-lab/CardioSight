@echo off
rem CardioSight Shunt Simulator - removes the installed copy and its shortcuts.
setlocal
set "DEST=%LOCALAPPDATA%\Programs\CardioSight Shunt Simulator"
set "NAME=CardioSight Shunt Simulator"
echo This removes "%DEST%" and the Desktop / Start Menu shortcuts.
choice /m "Continue"
if errorlevel 2 exit /b 0
for %%E in (lnk bat) do (
    del /q "%USERPROFILE%\Desktop\%NAME%.%%E" 2>nul
    del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\%NAME%.%%E" 2>nul
)
echo Removed shortcuts. Removing program files...
cd /d "%TEMP%"
(goto) 2>nul & rmdir /s /q "%DEST%" & echo Uninstalled. & pause
