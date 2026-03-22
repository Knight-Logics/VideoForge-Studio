# Download and Run VideoForge Studio on Windows

This version is designed to use the end user's own computer for rendering.

## What users need

- Windows 10 or 11
- Python 3.12 installed
- FFmpeg installed and added to PATH
- Internet connection only if using optional ElevenLabs or Stripe features

## Fast start

1. Download the latest portable release zip from GitHub Releases
2. Extract the zip to any folder
3. Double-click `install_videoforge.bat`
4. After setup completes, double-click `start_videoforge.bat`
5. Your browser opens to:
   - `http://127.0.0.1:5050`

## First-time setup details

### Python

Install Python 3.12 and check:
- "Add Python to PATH"

### FFmpeg

Install FFmpeg and make sure `ffmpeg` works in a new terminal.

## What happens when you run it

- The web interface opens locally in your browser
- Rendering uses your own computer resources
- No render workload is sent to Knight Logics infrastructure

## Common problems

### Python not found

Install Python 3.12 and reopen the script.

### FFmpeg not found

Install FFmpeg and add it to PATH.

### Browser does not open

Visit manually:
- `http://127.0.0.1:5050`

## Stop the app

Close the PowerShell window running the app or press `Ctrl+C`.
