@echo off
echo Building LoL Auto-Accept EXE...
pyinstaller --onefile --windowed main.py
echo.
echo Build complete! Check the 'dist' folder for main.exe
pause