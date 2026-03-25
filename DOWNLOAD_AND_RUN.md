# Download and Run VideoForge Studio on Windows

This version is designed to use the end user's own computer for rendering.

## Recommended download

Use the packaged Windows exe release.

What it includes:
- Bundled Python runtime
- Bundled `ffmpeg.exe`
- Bundled `ffprobe.exe`
- Standalone desktop window that embeds the same VideoForge UI

## EXE fast start

1. Download the latest `VideoForge-Studio-Windows-Exe.zip` from GitHub Releases
2. Extract the zip to any folder
3. Open the extracted `VideoForge-Studio` folder
4. Double-click `VideoForge-Studio.exe`
5. VideoForge opens in its own desktop window

If needed, you can still use the local browser URL:
- `http://127.0.0.1:5050`

## Source-mode fallback

Use this only if you want to run from source instead of the packaged exe.

### What users need for source mode

- Windows 10 or 11
- Python 3.12 installed
- FFmpeg installed and added to PATH

### Source-mode fast start

1. Download the portable source zip from GitHub Releases
2. Extract the zip to any folder
3. Double-click `install_videoforge.bat`
4. After setup completes, double-click `start_videoforge.bat`
5. VideoForge opens in its own desktop window

## Source-mode setup details

### Python

Install Python 3.12 and check:
- "Add Python to PATH"

### FFmpeg

Install FFmpeg and make sure `ffmpeg` works in a new terminal.

## What happens when you run it

- The web interface opens locally in your browser
- The same web interface is embedded in a standalone desktop window by default
- Rendering uses your own computer resources
- No render workload is sent to Knight Logics infrastructure

## Common problems

### EXE does not start

Try running `VideoForge-Studio.exe` from a normal folder like Desktop or Downloads, not from inside the zip.

### Python not found

Install Python 3.12 and reopen the script.

### FFmpeg not found

Install FFmpeg and add it to PATH.

### Window does not open

Run `VideoForge-Studio.exe` again from the extracted folder. If needed, set `VIDEOFORGE_UI_MODE=browser` and launch again to use the browser fallback.

### Browser fallback

Visit manually:
- `http://127.0.0.1:5050`

## Stop the app

Close the PowerShell window running the app or press `Ctrl+C`.
