@echo off
setlocal EnableExtensions

if "%~1"=="" (
  echo.
  echo CHATGPT ARCHIVE - STAGE 2: BUILD THE BROWSER
  echo --------------------------------------------
  echo Drag ChatGPT_Conversations_Only.zip onto this BAT file.
  echo.
  echo If you do not have that ZIP yet, first drag your ORIGINAL
  echo ChatGPT export ZIP onto prepare_windows.bat.
  echo.
  pause
  exit /b 1
)

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py -3"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE (
  echo.
  echo Python 3 was not found.
  echo Install Python 3 from https://www.python.org/downloads/
  echo During installation, select "Add python.exe to PATH" if offered.
  echo Then close this window and try again.
  echo.
  pause
  exit /b 1
)

echo.
echo Stage 2 of 2: building local HTML browser...
echo Input: %~f1
echo.
%PYEXE% "%~dp0chatgpt_archive_browser.py" "%~f1" --output "%~dp1ChatGPT_Archive_Browser" --overwrite
if errorlevel 1 (
  echo.
  echo Build failed. Read the error above.
  echo.
  pause
  exit /b 1
)

echo.
echo STAGE 2 COMPLETE.
echo Opening the archive index...
start "" "%~dp1ChatGPT_Archive_Browser\index.html"
echo.
pause