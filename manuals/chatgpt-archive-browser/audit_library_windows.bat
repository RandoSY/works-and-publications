@echo off
setlocal

if "%~1"=="" (
  echo.
  echo CHATGPT LIBRARY AUDIT
  echo =====================
  echo.
  echo Drag the ORIGINAL FULL ChatGPT export ZIP onto this BAT file.
  echo.
  echo IMPORTANT:
  echo   Do NOT use ChatGPT_Conversations_Only.zip.
  echo   Library Audit needs the full export so it can compare
  echo   library-files.json with the physical files in the export.
  echo.
  pause
  exit /b 1
)

set "INPUT=%~1"
set "OUT=%~dp1ChatGPT_Library_Audit"

echo.
echo CHATGPT LIBRARY AUDIT
echo Source: "%INPUT%"
echo Output: "%OUT%"
echo.
echo This is read-only. The original export will not be changed.
echo.

python "%~dp0audit_chatgpt_library.py" "%INPUT%" --output "%OUT%" --overwrite
if errorlevel 1 (
  echo.
  echo Audit failed. Read the error above.
  echo Your original export has not been changed.
  pause
  exit /b 1
)

echo.
echo Audit complete.
echo Opening the HTML report...
start "" "%OUT%\index.html"
pause
