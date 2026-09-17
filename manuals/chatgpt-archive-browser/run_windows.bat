@echo off
setlocal
if "%~1"=="" (
  echo Drag your ChatGPT export ZIP onto this BAT file,
  echo or run: run_windows.bat "C:\path\to\chatgpt-export.zip"
  pause
  exit /b 1
)
python "%~dp0chatgpt_archive_browser.py" "%~1" --output "%~dp1ChatGPT_Archive_Browser" --overwrite
if errorlevel 1 (
  echo.
  echo Build failed. See the error above.
  pause
  exit /b 1
)
echo.
echo Finished. Opening archive index...
start "" "%~dp1ChatGPT_Archive_Browser\index.html"
pause
