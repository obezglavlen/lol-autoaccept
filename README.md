# Auto Accept

A Windows desktop app that watches one selected process window for a saved image template and clicks the matching location automatically.

## Features

- Native Drag&Drop and file picker for PNG, JPG, JPEG, and BMP templates
- Process selector containing applications with visible windows
- Image search limited to the selected process window
- Automatic click at the center of a template match
- Persistent template and process selection between launches
- Start/Stop controls and live status messages

## Requirements

- Python 3.8+
- Windows 10/11

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. Start the app:

   ```bash
   python main.py
   ```

2. Drop a template image onto the image area or click **Choose image**.
3. Choose the target application from **Process window**. Use **Refresh** after opening a new application.
4. Keep the selected process window visible and click **Start scanning**.
5. Click **Stop** to end monitoring.

## Persistence

The app stores its state under `%LOCALAPPDATA%\LoLAutoAccept`:

- `accept_template.png` — normalized copy of the selected image
- `selected_process.json` — executable name, last PID, and window title

On restart, the app restores the template and resolves the saved process by PID or executable name.

## How it works

1. The selected window bounds are read from the process that owns the window.
2. Screenshots are restricted to those bounds.
3. OpenCV template matching searches the screenshot for the saved image.
4. A match at or above the configured confidence threshold is clicked using screen coordinates.

## Tips

- Use a tightly cropped and visually distinctive template.
- Keep the target window visible and unobstructed.
- If the process was opened after Auto Accept, press **Refresh** and select it.
- You can replace the image at any time by dropping or choosing another file.

## Troubleshooting

- **Process is missing:** ensure it has a visible, non-minimized window, then press **Refresh**.
- **Window cannot be found:** reselect the running process; its PID may have changed.
- **Template is not matched:** capture a clearer or more tightly cropped image.

## Build

```bash
pyinstaller --noconfirm --clean main.spec
```

The standalone executable is written to `dist\lolautoaccept.exe`.

## Files

- `main.py` — GUI and scanning logic
- `image_storage.py` — durable image storage
- `process_selection.py` — process selection and persistence
- `tests/` — automated test suite
- `main.spec` — PyInstaller configuration
