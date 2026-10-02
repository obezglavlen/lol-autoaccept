@echo off
echo Building LoL Auto-Accept EXE...
pyinstaller --noconfirm --clean main.spec
if errorlevel 1 exit /b %errorlevel%
echo.
echo Build complete! Check the 'dist' folder for lolautoaccept.exe
pause