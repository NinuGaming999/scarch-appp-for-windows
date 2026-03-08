import os
import queue
import sqlite3
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DB_NAME = "file_index.db"

CATEGORY_RULES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".ppt", ".pptx", ".xls", ".xlsx"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff"},
    "Videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm"},
    "Audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".html", ".css", ".json", ".xml"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".ps1"},
}


def detect_category(suffix: str) -> str:
    ext = suffix.lower()
    for category, extensions in CATEGORY_RULES.items():
        if ext in extensions:
            return category
    return "Other"


class FastIndexer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._setup_schema()
        self.lock = threading.Lock()

    def _setup_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE,
                name TEXT NOT NULL,
                extension TEXT,
                category TEXT,
                size INTEGER,
                modified REAL
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified);")
        self.conn.commit()

    def clear(self) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM files;")
            self.conn.commit()

    def bulk_insert(self, rows: list[tuple]) -> None:
        with self.lock:
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO files(path, name, extension, category, size, modified)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.conn.commit()

    def search(self, text: str, category: str | None = None, limit: int = 250) -> list[tuple]:
        text_like = f"%{text.lower()}%"
        params = [text_like]
        query = (
            "SELECT name, path, category, size, datetime(modified, 'unixepoch', 'localtime') "
            "FROM files WHERE lower(name) LIKE ?"
        )
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY modified DESC LIMIT ?"
        params.append(limit)
        cur = self.conn.execute(query, params)
        return cur.fetchall()

    def category_stats(self) -> list[tuple[str, int]]:
        cur = self.conn.execute(
            "SELECT category, COUNT(*) FROM files GROUP BY category ORDER BY COUNT(*) DESC"
        )
        return cur.fetchall()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows 11 Fast Search + File Categorizer")
        self.root.geometry("1200x700")

        self.indexer = FastIndexer(DB_NAME)
        self.scan_queue: queue.Queue[str] = queue.Queue()
        self.scanning = False
        self.selected_root = tk.StringVar(value=str(Path.home()))
        self.category_filter = tk.StringVar(value="All")

        self._build_ui()
        self._refresh_categories()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Folder / Drive:").pack(side="left")
        ttk.Entry(top, textvariable=self.selected_root, width=60).pack(side="left", padx=6)
        ttk.Button(top, text="Browse", command=self._choose_folder).pack(side="left")
        ttk.Button(top, text="Build / Rebuild Index", command=self._start_scan).pack(side="left", padx=8)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.status, foreground="blue").pack(side="right")

        search_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        search_frame.pack(fill="x")

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda _e: self._run_search())

        ttk.Label(search_frame, text="Category:").pack(side="left", padx=(12, 0))
        self.category_combo = ttk.Combobox(
            search_frame,
            textvariable=self.category_filter,
            state="readonly",
            values=["All"],
            width=20,
        )
        self.category_combo.pack(side="left", padx=6)
        self.category_combo.bind("<<ComboboxSelected>>", lambda _e: self._run_search())

        main = ttk.Panedwindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=4)

        ttk.Label(left, text="Category Counts", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.stats = tk.Text(left, height=30, width=25, state="disabled")
        self.stats.pack(fill="both", expand=True)

        columns = ("name", "category", "size", "modified", "path")
        self.tree = ttk.Treeview(right, columns=columns, show="headings")
        for col, width in [("name", 220), ("category", 120), ("size", 90), ("modified", 160), ("path", 520)]:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.selected_root.get())
        if folder:
            self.selected_root.set(folder)

    def _start_scan(self) -> None:
        if self.scanning:
            return
        root_path = self.selected_root.get().strip()
        if not root_path or not os.path.exists(root_path):
            messagebox.showerror("Invalid path", "Choose a valid Windows folder or drive.")
            return

        self.scanning = True
        self.status.set("Indexing started...")
        t = threading.Thread(target=self._scan_files, args=(root_path,), daemon=True)
        t.start()
        self.root.after(200, self._poll_queue)

    def _scan_files(self, root_path: str) -> None:
        start = time.time()
        self.indexer.clear()
        batch = []
        total = 0

        stack = [root_path]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                suffix = Path(entry.name).suffix
                                batch.append(
                                    (
                                        entry.path,
                                        entry.name,
                                        suffix.lower(),
                                        detect_category(suffix),
                                        stat.st_size,
                                        stat.st_mtime,
                                    )
                                )
                                total += 1
                                if len(batch) >= 2000:
                                    self.indexer.bulk_insert(batch)
                                    batch.clear()
                                    self.scan_queue.put(f"Indexed {total:,} files...")
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
                continue

        if batch:
            self.indexer.bulk_insert(batch)

        elapsed = time.time() - start
        self.scan_queue.put(f"DONE::{total}::{elapsed:.2f}")

    def _poll_queue(self) -> None:
        while not self.scan_queue.empty():
            msg = self.scan_queue.get()
            if msg.startswith("DONE::"):
                _, count, elapsed = msg.split("::")
                self.status.set(f"Done. Indexed {int(count):,} files in {elapsed}s")
                self.scanning = False
                self._refresh_categories()
                self._run_search()
                return
            self.status.set(msg)

        if self.scanning:
            self.root.after(200, self._poll_queue)

    def _refresh_categories(self) -> None:
        stats = self.indexer.category_stats()
        values = ["All"] + [name for name, _count in stats]
        self.category_combo["values"] = values
        if self.category_filter.get() not in values:
            self.category_filter.set("All")

        self.stats.config(state="normal")
        self.stats.delete("1.0", "end")
        for name, count in stats:
            self.stats.insert("end", f"{name:<15} {count:,}\n")
        self.stats.config(state="disabled")

    def _run_search(self) -> None:
        text = self.search_var.get().strip()
        cat = self.category_filter.get()
        rows = self.indexer.search(text, category=cat) if text else []

        for item in self.tree.get_children():
            self.tree.delete(item)

        for name, path, category, size, modified in rows:
            size_kb = f"{size / 1024:.1f} KB"
            self.tree.insert("", "end", values=(name, category, size_kb, modified, path))


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
