$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt
python -m pip install pyinstaller

python -m PyInstaller `
  --name LoLAutoAccept `
  --onefile `
  --noconsole `
  --add-data "config.yaml;." `
  --add-data "assets;assets" `
  main.py

Write-Host "Build done. Binary: dist/LoLAutoAccept.exe"

