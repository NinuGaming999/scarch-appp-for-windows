# Windows 11 Fast Search + File Categorizer

This project is a lightweight desktop app that indexes files on your Windows machine and lets you search quickly by filename with category filtering.

## Features

- Fast local indexing using `os.scandir` + SQLite.
- Automatic file categorization (Documents, Images, Videos, Code, etc.).
- Live search by filename.
- Category-based filtering.
- Built with Python standard library (`tkinter`, `sqlite3`) so no third-party dependency is required.

## Run on Windows 11

1. Install Python 3.10+.
2. Open PowerShell in the project folder.
3. Run:

```powershell
python app.py
```

## How to use

1. Choose a folder or drive (for example `C:\`).
2. Click **Build / Rebuild Index**.
3. Type in the search box to get instant results.
4. Use the category dropdown to narrow results.

## Notes

- The first index build can take time depending on disk size.
- Folders without access permissions are skipped automatically.
- The SQLite DB file (`file_index.db`) is created in the app folder.
