# User-Local Mode (Users Run Processing on Their Own Computers)

If your goal is for each user to consume their own CPU/GPU instead of your machine, distribute VideoForge as a local package.

## How it works

- The app runs on the user's own computer at http://127.0.0.1:5050
- FFmpeg rendering runs on that same user computer
- No remote render workload is sent to your hardware

## What this means operationally

Pros:
- No centralized hosting costs
- No server resource burden on your computer
- Better privacy for users working with local media

Cons:
- Users must install dependencies once (Python + FFmpeg)
- Performance varies by user hardware

## Distribution flow

1. Publish the repo or release zip
2. User downloads project/release
3. User runs install_local_user.ps1
4. User runs launch_local_user.ps1

## Build a portable release zip

Run:
- .\package_portable_release.ps1

Output:
- release/VideoForge-Studio-Portable.zip

## Practical resource expectations

Video rendering is compute-heavy.

Typical load drivers:
- Number and length of clips
- Output resolution and frame rate
- Narration/caption generation
- Simultaneous jobs

For best results, suggest users close other heavy apps while rendering.
