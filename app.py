import os
import queue
import sqlite3
import subprocess
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
        self.root.geometry("1260x760")
        self.root.configure(bg="#101726")

        self.indexer = FastIndexer(DB_NAME)
        self.scan_queue: queue.Queue[str] = queue.Queue()
        self.scanning = False
        self.selected_root = tk.StringVar(value=str(Path.home()))
        self.category_filter = tk.StringVar(value="All")
        self.status = tk.StringVar(value="Ready")
        self.search_var = tk.StringVar()
        self.editor_extensions = {".txt", ".md", ".py", ".json", ".xml", ".csv", ".log", ".ini", ".yaml", ".yml", ".html", ".css", ".js", ".ts"}

        self._status_tick = 0
        self._hero_step = 0

        self._build_style()
        self._build_ui()
        self._refresh_categories()
        self._animate_hero()
        self._animate_status()

    def _build_style(self) -> None:
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        bg = "#101726"
        panel = "#1A2438"
        panel_alt = "#162034"
        fg = "#E9EEF9"

        self.style.configure("Root.TFrame", background=bg)
        self.style.configure("Card.TFrame", background=panel)
        self.style.configure("AltCard.TFrame", background=panel_alt)
        self.style.configure("Title.TLabel", background=bg, foreground="#F6F8FF", font=("Segoe UI Semibold", 22))
        self.style.configure("Subtitle.TLabel", background=bg, foreground="#AFC3E5", font=("Segoe UI", 10))
        self.style.configure("Label.TLabel", background=panel, foreground=fg, font=("Segoe UI", 10))
        self.style.configure("Status.TLabel", background=panel, foreground="#9FD6FF", font=("Segoe UI", 10, "bold"))
        self.style.configure("Glow.TButton", font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(14, 8))
        self.style.map(
            "Glow.TButton",
            background=[("active", "#5D6DFF"), ("!disabled", "#495BFA")],
            foreground=[("!disabled", "#FFFFFF")],
        )
        self.style.configure("TEntry", fieldbackground="#0D1628", foreground="#EEF3FF", bordercolor="#2D3D59")
        self.style.configure("TCombobox", fieldbackground="#0D1628", background="#0D1628", foreground="#EEF3FF")

        self.style.configure("Treeview", background="#111A2B", fieldbackground="#111A2B", foreground="#ECF2FF", rowheight=28, borderwidth=0)
        self.style.configure("Treeview.Heading", background="#27314D", foreground="#DCE7FF", relief="flat", font=("Segoe UI Semibold", 10))
        self.style.map("Treeview", background=[("selected", "#364A77")])

        self.style.configure("Accent.Horizontal.TProgressbar", troughcolor="#0B1323", background="#4CC8FF", lightcolor="#4CC8FF", darkcolor="#4CC8FF", bordercolor="#0B1323")

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, style="Root.TFrame", padding=12)
        root_frame.pack(fill="both", expand=True)

        hero = ttk.Frame(root_frame, style="Root.TFrame")
        hero.pack(fill="x", pady=(0, 10))

        ttk.Label(hero, text="⚡ Hyper Search for Windows 11", style="Title.TLabel").pack(anchor="w")
        ttk.Label(hero, text="Fast index + smart categories + modern UI", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 8))

        self.hero_glow = tk.Canvas(hero, height=6, bg="#101726", highlightthickness=0)
        self.hero_glow.pack(fill="x")
        self.hero_bar = self.hero_glow.create_rectangle(0, 0, 200, 6, fill="#4CC8FF", outline="")

        controls = ttk.Frame(root_frame, style="Card.TFrame", padding=12)
        controls.pack(fill="x", pady=(4, 10))

        ttk.Label(controls, text="Folder / Drive", style="Label.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.selected_root, width=66).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(controls, text="Browse", style="Glow.TButton", command=self._choose_folder).grid(row=0, column=2, padx=4)
        ttk.Button(controls, text="Build / Rebuild Index", style="Glow.TButton", command=self._start_scan).grid(row=0, column=3, padx=(4, 0))

        ttk.Label(controls, text="Search", style="Label.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        search_entry = ttk.Entry(controls, textvariable=self.search_var, width=54)
        search_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        search_entry.bind("<KeyRelease>", lambda _e: self._run_search())

        ttk.Label(controls, text="Category", style="Label.TLabel").grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(10, 0))
        self.category_combo = ttk.Combobox(controls, textvariable=self.category_filter, state="readonly", values=["All"], width=20)
        self.category_combo.grid(row=1, column=3, sticky="w", pady=(10, 0))
        self.category_combo.bind("<<ComboboxSelected>>", lambda _e: self._run_search())

        self.progress = ttk.Progressbar(controls, style="Accent.Horizontal.TProgressbar", mode="indeterminate")
        self.progress.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(12, 4))
        self.progress.grid_remove()

        ttk.Label(controls, textvariable=self.status, style="Status.TLabel").grid(row=3, column=0, columnspan=4, sticky="w")
        controls.columnconfigure(1, weight=1)

        content = ttk.Panedwindow(root_frame, orient="horizontal")
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content, style="AltCard.TFrame", padding=10)
        right = ttk.Frame(content, style="Card.TFrame", padding=10)
        content.add(left, weight=1)
        content.add(right, weight=4)

        ttk.Label(left, text="Category Insights", style="Label.TLabel", font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(0, 6))
        self.stats = tk.Text(
            left,
            height=30,
            width=27,
            state="disabled",
            bg="#101A2E",
            fg="#CDE1FF",
            insertbackground="#FFFFFF",
            relief="flat",
            font=("Consolas", 10),
        )
        self.stats.pack(fill="both", expand=True)

        columns = ("name", "category", "size", "modified", "path")
        self.tree = ttk.Treeview(right, columns=columns, show="headings")
        widths = [("name", 240), ("category", 130), ("size", 100), ("modified", 170), ("path", 560)]
        for col, width in widths:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("even", background="#121E33")
        self.tree.tag_configure("odd", background="#0E1728")
        self.tree.bind("<Double-1>", self._on_result_open)

    def _animate_hero(self) -> None:
        width = max(self.hero_glow.winfo_width(), 200)
        bar_width = 260
        x = (self._hero_step % (width + bar_width)) - bar_width
        self.hero_glow.coords(self.hero_bar, x, 0, x + bar_width, 6)
        colors = ["#4CC8FF", "#66B3FF", "#829BFF", "#6FA9FF"]
        self.hero_glow.itemconfig(self.hero_bar, fill=colors[(self._hero_step // 8) % len(colors)])
        self._hero_step += 6
        self.root.after(45, self._animate_hero)

    def _animate_status(self) -> None:
        if self.scanning:
            dots = "." * (self._status_tick % 4)
            if "Indexing" in self.status.get() and not self.status.get().endswith("..."):
                self.status.set(self.status.get().split(".")[0] + dots)
        self._status_tick += 1
        self.root.after(350, self._animate_status)

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
        self.status.set("Indexing started")
        self.progress.grid()
        self.progress.start(9)

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
                                    self.scan_queue.put(f"Indexed {total:,} files")
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
                self.progress.stop()
                self.progress.grid_remove()
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
        self.stats.insert("end", "Category        Count\n", "head")
        self.stats.insert("end", "---------------------\n", "head")
        for name, count in stats:
            self.stats.insert("end", f"{name:<14} {count:,}\n")
        self.stats.config(state="disabled")

    def _run_search(self) -> None:
        text = self.search_var.get().strip()
        cat = self.category_filter.get()
        rows = self.indexer.search(text, category=cat) if text else []

        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, (name, path, category, size, modified) in enumerate(rows):
            size_kb = f"{size / 1024:.1f} KB"
            self.tree.insert("", "end", values=(name, category, size_kb, modified, path), tags=("even" if idx % 2 == 0 else "odd",))

    def _on_result_open(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item.get("values", [])
        if len(values) < 5:
            return
        file_name, category, size_label, modified, file_path = values
        self._show_file_window(file_path, file_name, category, size_label, modified)

    def _show_file_window(self, file_path: str, file_name: str, category: str, size_label: str, modified: str) -> None:
        if not os.path.exists(file_path):
            messagebox.showerror("Missing file", "The selected file no longer exists.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"File: {file_name}")
        win.geometry("860x620")
        win.configure(bg="#101726")

        top = ttk.Frame(win, style="Card.TFrame", padding=12)
        top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text=file_name, style="Label.TLabel", font=("Segoe UI Semibold", 14)).pack(anchor="w")
        ttk.Label(top, text=f"Category: {category}    Size: {size_label}    Modified: {modified}", style="Label.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(top, text=file_path, style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(win, style="Card.TFrame", padding=(12, 6))
        actions.pack(fill="x", padx=10)
        ttk.Button(actions, text="Open", style="Glow.TButton", command=lambda: self._open_file(file_path)).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Edit", style="Glow.TButton", command=lambda: self._focus_editor(win)).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Rename", style="Glow.TButton", command=lambda: self._rename_from_window(win, file_path)).pack(side="left")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        info_tab = ttk.Frame(notebook, style="AltCard.TFrame", padding=10)
        notebook.add(info_tab, text="Details")
        info_box = tk.Text(info_tab, bg="#101A2E", fg="#CDE1FF", relief="flat", font=("Consolas", 10), wrap="word")
        info_box.pack(fill="both", expand=True)
        info_box.insert(
            "end",
            f"Name      : {file_name}\n"
            f"Path      : {file_path}\n"
            f"Category  : {category}\n"
            f"Size      : {size_label}\n"
            f"Modified  : {modified}\n"
            f"Extension : {Path(file_path).suffix.lower() or '(none)'}\n",
        )
        info_box.config(state="disabled")

        editor_tab = ttk.Frame(notebook, style="Card.TFrame", padding=10)
        notebook.add(editor_tab, text="Editor")
        editor = tk.Text(editor_tab, bg="#0F1728", fg="#ECF3FF", insertbackground="#FFFFFF", relief="flat", font=("Consolas", 10))
        editor.pack(fill="both", expand=True)
        save_btn = ttk.Button(editor_tab, text="Save Changes", style="Glow.TButton")
        save_btn.pack(anchor="e", pady=(8, 0))

        win.current_file_path = file_path  # type: ignore[attr-defined]
        win.editor_widget = editor  # type: ignore[attr-defined]
        win.editor_save_btn = save_btn  # type: ignore[attr-defined]

        self._load_editor_content(win)

    def _open_file(self, file_path: str) -> None:
        try:
            if os.name == "nt":
                os.startfile(file_path)
            else:
                subprocess.Popen(["xdg-open", file_path])
        except OSError as exc:
            messagebox.showerror("Open failed", f"Could not open file:\n{exc}")

    def _focus_editor(self, file_win: tk.Toplevel) -> None:
        editor = getattr(file_win, "editor_widget", None)
        if editor is not None:
            editor.focus_set()

    def _rename_from_window(self, file_win: tk.Toplevel, file_path: str) -> None:
        folder = os.path.dirname(file_path)
        old_name = os.path.basename(file_path)

        rename_win = tk.Toplevel(file_win)
        rename_win.title("Rename file")
        rename_win.geometry("460x140")
        rename_win.configure(bg="#101726")
        frame = ttk.Frame(rename_win, style="Card.TFrame", padding=12)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame, text="New file name", style="Label.TLabel").pack(anchor="w")
        new_name_var = tk.StringVar(value=old_name)
        entry = ttk.Entry(frame, textvariable=new_name_var, width=50)
        entry.pack(fill="x", pady=(4, 10))
        entry.focus_set()

        def apply_rename() -> None:
            new_name = new_name_var.get().strip()
            if not new_name:
                messagebox.showerror("Invalid name", "File name cannot be empty.")
                return

            new_path = os.path.join(folder, new_name)
            try:
                os.rename(file_path, new_path)
            except OSError as exc:
                messagebox.showerror("Rename failed", f"Could not rename file:\n{exc}")
                return

            file_win.current_file_path = new_path  # type: ignore[attr-defined]
            file_win.title(f"File: {new_name}")
            rename_win.destroy()
            self.status.set(f"Renamed: {old_name} -> {new_name}")
            self._run_search()

        ttk.Button(frame, text="Apply Rename", style="Glow.TButton", command=apply_rename).pack(anchor="e")

    def _load_editor_content(self, file_win: tk.Toplevel) -> None:
        file_path = getattr(file_win, "current_file_path", "")
        editor = getattr(file_win, "editor_widget", None)
        save_btn = getattr(file_win, "editor_save_btn", None)
        if not file_path or editor is None or save_btn is None:
            return

        ext = Path(file_path).suffix.lower()
        editor.delete("1.0", "end")

        if ext not in self.editor_extensions:
            editor.insert("1.0", "This file type is not editable in-app.\nUse Open to edit with its native app.")
            editor.config(state="disabled")
            save_btn.config(state="disabled")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            editor.insert("1.0", "Unable to edit this file as UTF-8 text.")
            editor.config(state="disabled")
            save_btn.config(state="disabled")
            return
        except OSError as exc:
            editor.insert("1.0", f"Failed to read file:\n{exc}")
            editor.config(state="disabled")
            save_btn.config(state="disabled")
            return

        editor.config(state="normal")
        editor.insert("1.0", content)
        save_btn.config(state="normal", command=lambda: self._save_editor_content(file_win))

    def _save_editor_content(self, file_win: tk.Toplevel) -> None:
        file_path = getattr(file_win, "current_file_path", "")
        editor = getattr(file_win, "editor_widget", None)
        if not file_path or editor is None:
            return

        content = editor.get("1.0", "end-1c")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save file:\n{exc}")
            return

        self.status.set(f"Saved changes to: {os.path.basename(file_path)}")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
