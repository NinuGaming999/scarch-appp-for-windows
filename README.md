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

## Run on Windows 11 (development)

1. Install Python 3.10+.
2. Open PowerShell in the project folder.
3. Run:

```powershell
python app.py
```

## Build final distributable installer (recommended)

This project now includes a full Windows packaging flow that creates:

- a **single-file app executable**: `dist\HyperSearch.exe`
- a **one-click installer executable**: `dist_installer\HyperSearchInstaller.exe`

The installer will:

- install the app into `Program Files\HyperSearch`
- add Start Menu entry
- optionally add Desktop shortcut
- support standard uninstall from Windows Apps/Programs

### Steps

1. Install **Inno Setup 6**: https://jrsoftware.org/isdl.php
2. From PowerShell in project root, run:

```powershell
.\build_windows.ps1
```

3. Share `dist_installer\HyperSearchInstaller.exe` to other PCs.
4. Double-click installer on target machine and follow setup wizard.

> If you only want portable single EXE (no installer), run:

```powershell
.\build_windows.ps1 -SkipInstaller
```

## How to use

1. Choose a folder or drive (for example `C:\`).
2. Click **Build / Rebuild Index**.
3. Type in the search box to get instant results.
4. Use the category dropdown to narrow results.
5. Double-click any result to manage it inside the app (open/edit/rename).

## Notes

- The first index build can take time depending on disk size.
- Folders without access permissions are skipped automatically.
- The SQLite DB file (`file_index.db`) is created in the app folder.
