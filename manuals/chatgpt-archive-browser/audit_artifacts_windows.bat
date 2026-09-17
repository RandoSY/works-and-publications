@echo off
setlocal
if "%~1"=="" (
  echo.
  echo CHATGPT ARTIFACT PRESERVATION AUDIT
  echo.
  echo Drag your ORIGINAL FULL ChatGPT export ZIP onto this BAT file.
  echo This checks whether downloadable ZIPs, code, documents, PCB files,
  echo and other artifacts referenced in conversations physically survive.
  echo.
  pause
  exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found in PATH.
  echo Install Python 3, then try again.
  pause
  exit /b 1
)
set "OUT=%~dp1ChatGPT_Artifact_Audit"
if exist "%OUT%" (
  echo.
  echo Existing output folder found:
  echo   %OUT%
  echo Rename or delete it before running again.
  pause
  exit /b 1
)
python "%~dp0audit_chatgpt_artifacts.py" "%~1" -o "%OUT%"
if errorlevel 1 (
  echo.
  echo Audit failed. Read the error above.
  pause
  exit /b 1
)
echo.
echo Finished. Opening report...
start "" "%OUT%\index.html"
pause
