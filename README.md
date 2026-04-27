# LoL Auto Accept (Windows)

Windows utility on Python. Watches League of Legends client window. Detects `Accept` button by template image. Clicks once with cooldown.

## Features
- Window lookup by title substring (`League of Legends`)
- Client-region capture only (no full-screen polling)
- OpenCV template matching with threshold + multi-scale
- Single-click guard with cooldown
- Emergency stop hotkey (`F10` by default)

## Project files
- `main.py` - app loop
- `window_probe.py` - WinAPI window detection + client coordinates
- `vision.py` - template loading + matching
- `input_click.py` - click injection + cooldown guard
- `config.yaml` - runtime settings
- `assets/accept_template.png` - your button template image

## Install
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Calibrate template (`assets/accept_template.png`)
1. Open LoL client and wait until match accept dialog appears.
2. Take screenshot of client region.
3. Crop tight rectangle around only the `Accept` button text/button.
4. Save as `assets/accept_template.png`.
5. Start with `match_threshold: 0.86`; adjust to `0.88-0.93` if false positives.

## Run
```powershell
python .\main.py
```

Stop by hotkey from config (`F10`) or Ctrl+C in terminal.

## Config
Main keys in `config.yaml`:
- `window_title_contains`
- `template_path`
- `poll_interval_ms`
- `match_threshold`
- `click_cooldown_sec`
- `hotkey_stop`
- `multi_scale.enabled`
- `multi_scale.scales`

## Build EXE
```powershell
.\build.ps1
```

Output: `dist/LoLAutoAccept.exe`

## Notes
- Run as normal user first. If clicks blocked by privilege mismatch, run app with same privileges as LoL client.
- UI updates in LoL can break template; recapture template after patches.
- DPI scaling can reduce accuracy; keep Windows scale stable or tune `multi_scale.scales`.
