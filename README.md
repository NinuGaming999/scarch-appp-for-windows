# Windows 11 Fast Search + File Categorizer

This project is a lightweight desktop app that indexes files on your Windows machine and lets you search quickly by filename with category filtering.

## Features

- Fast local indexing using `os.scandir` + SQLite.
- Automatic file categorization (Documents, Images, Videos, Code, etc.).
- Live search by filename.
- Category-based filtering.
- Modern, animated UI (dark theme, glowing header animation, animated progress bar, zebra-striped result grid).
- Double-click a result to open an in-app file panel with actions: **Open**, **Edit** (text-based files), and **Rename**.
- Built with Python standard library (`tkinter`, `sqlite3`) so no third-party dependency is required.

## For end users (normal consumers)

You only need **one file**: `HyperSearchInstaller.exe`.

After double-clicking that installer:

- app installs fully (no Python installation needed)
- app runs normally without any extra downloads
- Start Menu shortcut is created
- Desktop shortcut is created
- app can be uninstalled from Windows Installed Apps

> End users do **not** need Python, pip, or any developer tools.

## Build final distributable installer (for app owner/developer)

This repository includes a full Windows packaging flow that creates:

- `dist\HyperSearch.exe` (single-file app executable)
- `dist_installer\HyperSearchInstaller.exe` (the one-click installer you share)

### Steps (on your build machine only)

1. Use a **Windows machine** (required).
2. Install **Inno Setup 6**: https://jrsoftware.org/isdl.php
3. Open PowerShell in the project root.
4. Run:

```powershell
.\build_windows.ps1
```

5. Share only this file with users:

```text
dist_installer\HyperSearchInstaller.exe
```

## Fix: "This app can’t run on your PC"

If you see this message when opening `HyperSearchInstaller.exe`, usually one of these happened:

1. The installer was built on Linux/macOS (invalid for Windows).  
   - Rebuild on Windows using `build_windows.ps1`.
2. The downloaded file is incomplete/corrupted.  
   - Download again and verify SHA256 hash printed by the build script.
3. The file was blocked by Windows after internet download.  
   - Right click installer → **Properties** → **Unblock** (if shown) → Apply.
4. You are launching from inside ZIP without extracting.  
   - Extract ZIP first, then run installer.

## Run from source (development only)

1. Install Python 3.10+.
2. Open PowerShell in the project folder.
3. Run:

```powershell
python app.py
```

## How to use the app

1. Choose a folder or drive (for example `C:\`).
2. Click **Build / Rebuild Index**.
3. Type in the search box to get instant results.
4. Use the category dropdown to narrow results.
5. Double-click any result to manage it inside the app (open/edit/rename).

## Notes

- The first index build can take time depending on disk size.
- Folders without access permissions are skipped automatically.
- The SQLite DB file (`file_index.db`) is created in the app folder.
