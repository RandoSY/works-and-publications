@echo off
setlocal
if "%~1"=="" (
  echo Drag the ORIGINAL ChatGPT export ZIP onto this file.
  echo It will only inspect the ZIP directory; it will not extract the archive.
  pause
  exit /b 1
)
set "OUT=%~dp1ChatGPT_Export_Census"
python "%~dp0chatgpt_export_spy.py" "%~1" -o "%OUT%"
if errorlevel 1 (
  echo.
  echo Census failed. See the error above.
  pause
  exit /b 1
)
echo.
echo Finished. Opening the census report...
start "" "%OUT%\index.html"
pause
