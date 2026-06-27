# LoL Auto-Accept App

A simple GUI application that monitors the League of Legends client window and automatically clicks the "Accept" button when it appears.

## Features

- Simple tkinter GUI with Start, Stop, and Image Upload buttons
- Upload a screenshot of the "Accept" button for template matching
- Automatically detects and clicks the accept button when the game is ready
- Visual status indicators

## Requirements

- Python 3.8+
- Windows (tested on Windows 10/11)
- League of Legends client installed

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have the required packages:

```bash
pip install pygetwindow pyautogui opencv-python Pillow
```

## Usage

1. **Launch the app:**
   ```bash
   python main.py
   ```

2. **Upload an image:**
   - Click "Browse" to select a screenshot of the "Accept" button from the League client
   - The image will be displayed in the UI

3. **Attach the League window:**
   - Click on the League of Legends client window to make it the active window

4. **Start monitoring:**
   - Click "Start" to begin monitoring for the accept button

5. **Stop when done:**
   - Click "Stop" to stop monitoring

## How it works

1. The app uses template matching to find the accept button by comparing your uploaded image
2. It continuously monitors the League client window for the accept button
3. When found, it automatically clicks the button using pyautogui

## Tips

- For best results, upload a clear screenshot of the accept button (without too much surrounding UI)
- The app works best when the League client window is visible and active
- You can upload a new image at any time by clicking "Browse"

## Troubleshooting

- **"No League window found"**: Make sure the League client is running and has a window
- **"Window not visible"**: Click on the League window to make it visible
- **Template matching fails**: Try uploading a different image of the accept button

## Files

- `main.py` - Main application code
- `requirements.txt` - Python dependencies
- `README.md` - This file
