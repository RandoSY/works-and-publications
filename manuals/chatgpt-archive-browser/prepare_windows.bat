@echo off
setlocal EnableExtensions

if "%~1"=="" (
  echo.
  echo CHATGPT ARCHIVE - STAGE 1: PREPARE CONVERSATION ZIP
  echo --------------------------------------------------
  echo Drag your ORIGINAL ChatGPT export ZIP onto this BAT file.
  echo.
  echo This will NOT change the original ZIP.
  echo It creates ChatGPT_Conversations_Only.zip beside it.
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
echo Stage 1 of 2: collecting conversation JSON files...
echo Input: %~f1
echo.
%PYEXE% "%~dp0prepare_conversations_zip.py" "%~f1" --output "%~dp1ChatGPT_Conversations_Only.zip" --overwrite
if errorlevel 1 (
  echo.
  echo Preparation failed. Read the error above. Your original export was not changed.
  echo.
  pause
  exit /b 1
)

echo.
echo STAGE 1 COMPLETE.
echo Next: drag ChatGPT_Conversations_Only.zip onto run_windows.bat
if exist "%~dp1ChatGPT_Conversations_Only.zip" explorer /select,"%~dp1ChatGPT_Conversations_Only.zip"
echo.
pause