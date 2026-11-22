import os
import sys
import json
import queue
import signal
import shutil
import threading
import subprocess
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from datetime import datetime

# ============================================================
# Theme
# ============================================================
BG           = "#0f1115"
CARD         = "#171a21"
CARD_ALT     = "#1d222b"
TEXT         = "#e7eaf0"
MUTED        = "#9aa4b2"
ACCENT       = "#2f80ed"
ACCENT_HOVER = "#2569c7"
SUCCESS      = "#2ecc71"
ERROR        = "#ff5c5c"
WARNING      = "#f1c40f"
BORDER       = "#2a303b"
ENTRY_BG     = "#11151b"

FONT         = ("Segoe UI", 10)
FONT_BOLD    = ("Segoe UI", 10, "bold")
FONT_TITLE   = ("Segoe UI", 15, "bold")
FONT_SMALL   = ("Segoe UI", 9)

CONFIG_FILE = Path.home() / ".app_builder_gui.json"


# ============================================================
# Config Persistence
# ============================================================
def load_config():
    defaults = {
        "recent": [],
        "geometry": "960x760",
        "output_dest": "portables",  # "portables" or "same_folder"
        "onefile": True,
        "windowed": False,
        "upx": False,
        "auto_run": True,
        "install_deps": True,
        "custom_name": "",
        "add_data": "",
        "hidden_imports": "",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
    return defaults


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ============================================================
# Main Application GUI
# ============================================================
class AppBuilderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        self.title("App Builder - PY to EXE")
        self.geometry(self.cfg.get("geometry", "960x760"))
        self.minsize(860, 620)
        self.configure(bg=BG)

        self.log_queue = queue.Queue()
        self.build_process = None
        self.is_building = False
        self.cancel_requested = False
        self.last_exe_path = None

        # Form variables
        self.script_path_var    = tk.StringVar()
        self.icon_path_var      = tk.StringVar()
        self.output_dest_var    = tk.StringVar(value=self.cfg.get("output_dest", "portables"))
        self.custom_name_var    = tk.StringVar(value=self.cfg.get("custom_name", ""))
        self.add_data_var       = tk.StringVar(value=self.cfg.get("add_data", ""))
        self.hidden_imports_var = tk.StringVar(value=self.cfg.get("hidden_imports", ""))

        self.auto_run_var       = tk.BooleanVar(value=self.cfg.get("auto_run", True))
        self.install_deps_var   = tk.BooleanVar(value=self.cfg.get("install_deps", True))
        self.onefile_var        = tk.BooleanVar(value=self.cfg.get("onefile", True))
        self.windowed_var       = tk.BooleanVar(value=self.cfg.get("windowed", False))
        self.upx_var            = tk.BooleanVar(value=self.cfg.get("upx", False))
        self.autoscroll_var     = tk.BooleanVar(value=True)
        self.status_var         = tk.StringVar(value="Ready")

        self._build_ui()
        self.after(50, self._process_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------------------------------------
    # UI Layout (Optimized for Large Log Area)
    # ----------------------------------------------------------
    def _build_ui(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True, padx=14, pady=12)

        # Header - Compact
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="Python to Executable Builder", bg=BG, fg=TEXT, font=FONT_TITLE).pack(side="left")
        tk.Label(
            header,
            text="• PyInstaller packaging suite",
            bg=BG,
            fg=MUTED,
            font=FONT_SMALL,
        ).pack(side="left", padx=(8, 0), pady=(3, 0))

        # Main configuration card (Fixed height, only takes needed space)
        card = tk.Frame(root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", expand=False, pady=(0, 8))
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=14, pady=10)

        # Script row with Browse + Recent Dropdown
        self._build_script_row(inner)

        # Icon row
        self._path_row(
            inner,
            "Icon (.ico)",
            self.icon_path_var,
            self.browse_icon,
            "Select an optional icon file",
        )

        # Destination & flags row (Compact single bar)
        settings_bar = tk.Frame(inner, bg=CARD)
        settings_bar.pack(fill="x", pady=(2, 6))

        tk.Label(settings_bar, text="Save to:", bg=CARD, fg=TEXT, font=FONT_BOLD).pack(side="left", padx=(0, 6))
        self._radio(settings_bar, self.output_dest_var, "portables", "portables/ folder")
        self._radio(settings_bar, self.output_dest_var, "same_folder", "Same folder as script")

        tk.Frame(settings_bar, width=1, bg=BORDER).pack(side="left", fill="y", padx=10, pady=2)
        self._checkbox(settings_bar, self.install_deps_var, "Install requirements.txt")
        self._checkbox(settings_bar, self.auto_run_var, "Auto-run on success")

        # PyInstaller options row
        adv_bar = tk.Frame(inner, bg=CARD)
        adv_bar.pack(fill="x", pady=(2, 6))

        tk.Label(adv_bar, text="Mode:", bg=CARD, fg=TEXT, font=FONT_BOLD).pack(side="left", padx=(0, 6))
        self._checkbox(adv_bar, self.onefile_var, "Single File (--onefile)")
        self._checkbox(adv_bar, self.windowed_var, "No Console (--windowed)")
        self._checkbox(adv_bar, self.upx_var, "UPX Compress")

        # Compact 2-column input fields
        inputs_grid = tk.Frame(inner, bg=CARD)
        inputs_grid.pack(fill="x", pady=(2, 6))

        # Column 1: Custom Name & Add Data
        col1 = tk.Frame(inputs_grid, bg=CARD)
        col1.pack(side="left", fill="x", expand=True, padx=(0, 8))

        r_name = tk.Frame(col1, bg=CARD)
        r_name.pack(fill="x", pady=2)
        tk.Label(r_name, text="EXE Name:", bg=CARD, fg=MUTED, font=FONT_SMALL, width=11, anchor="w").pack(side="left")
        tk.Entry(
            r_name,
            textvariable=self.custom_name_var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=FONT_SMALL,
        ).pack(side="left", fill="x", expand=True, ipady=3)

        r_data = tk.Frame(col1, bg=CARD)
        r_data.pack(fill="x", pady=2)
        tk.Label(r_data, text="Add Data:", bg=CARD, fg=MUTED, font=FONT_SMALL, width=11, anchor="w").pack(side="left")
        tk.Entry(
            r_data,
            textvariable=self.add_data_var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=FONT_SMALL,
        ).pack(side="left", fill="x", expand=True, ipady=3)

        # Column 2: Hidden Imports
        col2 = tk.Frame(inputs_grid, bg=CARD)
        col2.pack(side="left", fill="x", expand=True, padx=(8, 0))

        r_imp = tk.Frame(col2, bg=CARD)
        r_imp.pack(fill="x", pady=2)
        tk.Label(r_imp, text="Hidden Imports:", bg=CARD, fg=MUTED, font=FONT_SMALL, width=14, anchor="w").pack(side="left")
        tk.Entry(
            r_imp,
            textvariable=self.hidden_imports_var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=FONT_SMALL,
        ).pack(side="left", fill="x", expand=True, ipady=3)

        r_hint = tk.Frame(col2, bg=CARD)
        r_hint.pack(fill="x", pady=2)
        tk.Label(
            r_hint,
            text="Tip: comma-separated modules (e.g. PIL, requests, sqlite3)",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        # Action Buttons & Progress Bar
        actions = tk.Frame(inner, bg=CARD)
        actions.pack(fill="x", pady=(6, 0))

        self.build_btn = self._button(actions, "Build Executable", self.start_build, accent=True)
        self.build_btn.pack(side="left")

        self.cancel_btn = self._button(actions, "Cancel", self.cancel_build, accent=False)
        self.cancel_btn.pack(side="left", padx=(8, 0))
        self.cancel_btn.configure(state="disabled")

        self._button(actions, "Open Output Folder", self.open_output, accent=False).pack(side="left", padx=(8, 0))
        self._button(actions, "Copy EXE Path", self.copy_exe_path, accent=False).pack(side="left", padx=(8, 0))

        # Progress bar
        prog_frame = tk.Frame(inner, bg=CARD)
        prog_frame.pack(fill="x", pady=(8, 0))

        self.progress = ttk.Progressbar(prog_frame, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TProgressbar",
            troughcolor=ENTRY_BG,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=8,
        )

        tk.Label(prog_frame, textvariable=self.status_var, bg=CARD, fg=MUTED, font=FONT_SMALL).pack(
            side="left", padx=(10, 0)
        )

        # ============================================================
        # EXPANDED LOG CARD (Occupies all remaining vertical space)
        # ============================================================
        log_card = tk.Frame(root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        log_card.pack(fill="both", expand=True)

        # Log Header with integrated controls
        log_header = tk.Frame(log_card, bg=CARD)
        log_header.pack(fill="x", padx=12, pady=(6, 4))

        tk.Label(log_header, text="Build Output & Diagnostics", bg=CARD, fg=TEXT, font=FONT_BOLD).pack(side="left")

        # Right-side controls in log header
        self._button(log_header, "Clear Log", self.clear_log, accent=False, small=True).pack(side="right", padx=(4, 0))
        self._button(log_header, "Copy Log", self.copy_log, accent=False, small=True).pack(side="right", padx=(4, 0))
        self._checkbox(log_header, self.autoscroll_var, "Auto-scroll").pack(side="right", padx=(10, 4))

        # Log Body Frame with custom text + scrollbar
        log_body = tk.Frame(log_card, bg=ENTRY_BG)
        log_body.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        scrollbar = ttk.Scrollbar(log_body, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_body,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            padx=10,
            pady=8,
            yscrollcommand=scrollbar.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Color tags
        self.log_text.tag_configure("info", foreground=TEXT)
        self.log_text.tag_configure("muted", foreground=MUTED)
        self.log_text.tag_configure("success", foreground=SUCCESS)
        self.log_text.tag_configure("error", foreground=ERROR)
        self.log_text.tag_configure("warning", foreground=WARNING)
        self.log_text.tag_configure("cmd", foreground=ACCENT)

        self._log("Ready. Select a target Python script and click Build Executable.", "muted")

    # ----------------------------------------------------------
    # UI Component Helpers
    # ----------------------------------------------------------
    def _build_script_row(self, parent):
        wrapper = tk.Frame(parent, bg=CARD)
        wrapper.pack(fill="x", pady=(0, 6))

        row = tk.Frame(wrapper, bg=CARD)
        row.pack(fill="x")

        tk.Label(row, text="Target Script:", bg=CARD, fg=TEXT, font=FONT_BOLD, width=12, anchor="w").pack(side="left")

        tk.Entry(
            row,
            textvariable=self.script_path_var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=FONT,
        ).pack(side="left", fill="x", expand=True, ipady=4)

        self._button(row, "Browse", self.browse_script, accent=False).pack(side="left", padx=(6, 0))
        self.recent_btn = self._button(row, "Recent ▾", self._show_recent_menu, accent=False)
        self.recent_btn.pack(side="left", padx=(4, 0))

    def _path_row(self, parent, label, var, browse_cmd, hint):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 6))

        tk.Label(row, text=label + ":", bg=CARD, fg=TEXT, font=FONT_BOLD, width=12, anchor="w").pack(side="left")

        tk.Entry(
            row,
            textvariable=var,
            bg=ENTRY_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=FONT,
        ).pack(side="left", fill="x", expand=True, ipady=4)

        self._button(row, "Browse", browse_cmd, accent=False).pack(side="left", padx=(6, 0))

    def _button(self, parent, text, command, accent=True, small=False):
        bg = ACCENT if accent else CARD_ALT
        hover = ACCENT_HOVER if accent else "#252b36"
        fg = "#ffffff" if accent else TEXT
        padx = 9 if small else 12
        pady = 4 if small else 6
        font = FONT_SMALL if small else FONT_BOLD

        btn = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            padx=padx,
            pady=pady,
            font=font,
            cursor="hand2",
            relief="flat",
            takefocus=1,
        )

        def on_enter(_):
            if getattr(btn, "state", "normal") != "disabled":
                btn.configure(bg=hover)

        def on_leave(_):
            if getattr(btn, "state", "normal") != "disabled":
                btn.configure(bg=bg)

        def on_click(_):
            if getattr(btn, "state", "normal") != "disabled":
                command()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<Button-1>", on_click)
        btn.bind("<Return>", on_click)
        btn.bind("<space>", on_click)

        def configure(**kwargs):
            if "state" in kwargs:
                btn.state = kwargs["state"]
                if kwargs["state"] == "disabled":
                    tk.Label.configure(btn, bg="#2a303b", fg="#606775", cursor="arrow")
                else:
                    tk.Label.configure(btn, bg=bg, fg=fg, cursor="hand2")
            else:
                tk.Label.configure(btn, **kwargs)

        btn.configure = configure
        btn.state = "normal"
        return btn

    def _checkbox(self, parent, var, text):
        cb = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            bg=CARD,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=CARD,
            activeforeground=TEXT,
            font=FONT_SMALL,
            anchor="w",
            relief="flat",
        )
        cb.pack(side="left", padx=(0, 12))
        return cb

    def _radio(self, parent, var, value, text):
        rb = tk.Radiobutton(
            parent,
            text=text,
            variable=var,
            value=value,
            bg=CARD,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=CARD,
            activeforeground=TEXT,
            font=FONT_SMALL,
            relief="flat",
        )
        rb.pack(side="left", padx=(0, 10))
        return rb

    # ----------------------------------------------------------
    # Recent Scripts Menu
    # ----------------------------------------------------------
    def _show_recent_menu(self):
        recent = self.cfg.get("recent", [])
        menu = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground="#ffffff")

        if not recent:
            menu.add_command(label="(No recent scripts)", state="disabled")
        else:
            for p in recent:
                menu.add_command(label=p, command=lambda path=p: self._select_recent(path))
            menu.add_separator()
            menu.add_command(label="Clear History", command=self._clear_recent)

        try:
            x = self.recent_btn.winfo_rootx()
            y = self.recent_btn.winfo_rooty() + self.recent_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _select_recent(self, path):
        if os.path.exists(path):
            self.script_path_var.set(path)
        else:
            messagebox.showwarning("Missing File", f"File no longer exists:\n{path}")

    def _clear_recent(self):
        self.cfg["recent"] = []
        save_config(self.cfg)

    # ----------------------------------------------------------
    # Thread-Safe Logging & UI Queue Processing
    # ----------------------------------------------------------
    def _log(self, msg, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
        if self.autoscroll_var.get():
            self.log_text.see("end")

    def _queue_log(self, msg, tag="info"):
        self.log_queue.put(("log", (msg, tag)))

    def _queue_progress(self, val, status=None):
        self.log_queue.put(("progress", (val, status)))

    def _queue_finished(self, status_text, success=False, exe_path=None):
        self.log_queue.put(("finished", (status_text, success, exe_path)))

    def _process_log_queue(self):
        try:
            while True:
                item_type, data = self.log_queue.get_nowait()
                if item_type == "log":
                    msg, tag = data
                    self._log(msg, tag)
                elif item_type == "progress":
                    val, status = data
                    self.progress["value"] = val
                    if status is not None:
                        self.status_var.set(status)
                elif item_type == "finished":
                    status_text, success, exe_path = data
                    self.is_building = False
                    self.build_process = None
                    self.build_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.status_var.set(status_text)
                    if success and exe_path:
                        self.last_exe_path = exe_path
        except queue.Empty:
            pass
        self.after(50, self._process_log_queue)

    def clear_log(self):
        self.log_text.delete("1.0", "end")
        self._log("Log cleared.", "muted")

    def copy_log(self):
        content = self.log_text.get("1.0", "end-1c")
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_var.set("Log copied to clipboard")

    # ----------------------------------------------------------
    # File & Path Helpers
    # ----------------------------------------------------------
    def browse_script(self):
        path = filedialog.askopenfilename(
            title="Select Python script",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if path:
            self.script_path_var.set(path)
            self._add_recent(path)

    def browse_icon(self):
        path = filedialog.askopenfilename(
            title="Select icon file",
            filetypes=[("Icon files", "*.ico"), ("All files", "*.*")],
        )
        if path:
            self.icon_path_var.set(path)

    def _add_recent(self, path):
        recent = self.cfg.get("recent", [])
        path = str(Path(path).resolve())
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.cfg["recent"] = recent[:10]
        save_config(self.cfg)

    def open_output(self):
        if self.last_exe_path and Path(self.last_exe_path).exists():
            folder = Path(self.last_exe_path).parent
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        else:
            messagebox.showinfo("No output", "No successful build has completed yet.")

    def copy_exe_path(self):
        if self.last_exe_path and Path(self.last_exe_path).exists():
            self.clipboard_clear()
            self.clipboard_append(self.last_exe_path)
            self.status_var.set("Path copied")
            self._log(f"Copied to clipboard: {self.last_exe_path}", "success")
        else:
            messagebox.showinfo("No output", "No successful build has completed yet.")

    # ----------------------------------------------------------
    # Build Process Control & Termination
    # ----------------------------------------------------------
    def start_build(self):
        if self.is_building:
            return

        script_path = self.script_path_var.get().strip()
        icon_path = self.icon_path_var.get().strip() or None

        if not script_path:
            messagebox.showerror("Missing script", "Please select a target Python script.")
            return
        if not os.path.exists(script_path):
            messagebox.showerror("Invalid path", f"Script not found:\n{script_path}")
            return
        if icon_path and not os.path.exists(icon_path):
            messagebox.showerror("Invalid icon", f"Icon not found:\n{icon_path}")
            return

        self._add_recent(script_path)
        self.is_building = True
        self.cancel_requested = False
        self.last_exe_path = None
        self.build_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress["value"] = 0
        self.status_var.set("Starting…")

        threading.Thread(target=self._build_worker, args=(script_path, icon_path), daemon=True).start()

    def cancel_build(self):
        if not self.is_building:
            return
        self.cancel_requested = True
        self._queue_log("Cancel requested by user…", "warning")

        if self.build_process and self.build_process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.build_process.pid)],
                        capture_output=True,
                        check=False,
                    )
                else:
                    os.killpg(os.getpgid(self.build_process.pid), signal.SIGTERM)
            except Exception as e:
                self._queue_log(f"Process termination warning: {e}", "warning")

    def _run_streaming(self, cmd, cwd=None):
        self._queue_log(f"$ {' '.join(str(c) for c in cmd)}", "cmd")

        kwargs = {
            "cwd": cwd,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "universal_newlines": True,
        }
        if sys.platform != "win32":
            kwargs["preexec_fn"] = os.setsid

        try:
            self.build_process = subprocess.Popen(cmd, **kwargs)
        except FileNotFoundError as e:
            self._queue_log(f"Executable not found: {e}", "error")
            return 127

        try:
            for line in self.build_process.stdout:
                if self.cancel_requested:
                    break
                line = line.rstrip()
                if not line:
                    continue
                lower = line.lower()
                if any(x in lower for x in ("error", "failed", "traceback")):
                    tag = "error"
                elif "warning" in lower:
                    tag = "warning"
                else:
                    tag = "info"
                self._queue_log(line, tag)
        except Exception as e:
            self._queue_log(f"Stream read error: {e}", "error")

        self.build_process.wait()
        return self.build_process.returncode

    # ----------------------------------------------------------
    # Core Build Worker
    # ----------------------------------------------------------
    def _build_worker(self, script_path, icon_path):
        script_path = str(Path(script_path).resolve())
        script_dir  = Path(script_path).parent
        base_name   = Path(script_path).stem

        # Sanitize custom name
        raw_name = self.custom_name_var.get().strip()
        custom_name = re.sub(r'[\\/*?:"<>|]', "", raw_name).strip() if raw_name else base_name
        if not custom_name:
            custom_name = base_name

        # Determine target output folder
        if self.output_dest_var.get() == "same_folder":
            out_dir = script_dir
        else:
            out_dir = script_dir / "portables"

        # Temporary working directories
        temp_dist  = script_dir / ".pybuilder_dist"
        temp_build = script_dir / ".pybuilder_build"
        temp_spec  = script_dir / f"{custom_name}.spec"

        try:
            # ---------------- Step 1: Requirements ----------------
            self._queue_progress(5, "Checking requirements…")
            self._queue_log("Step 1/4  →  Checking dependencies", "info")

            has_pipreqs = False
            try:
                check_rc = subprocess.run(
                    [sys.executable, "-m", "pipreqs.pipreqs", "--version"],
                    capture_output=True,
                    text=True,
                )
                has_pipreqs = (check_rc.returncode == 0)
            except Exception:
                has_pipreqs = False

            req_file = script_dir / "requirements.txt"
            if has_pipreqs:
                rc = self._run_streaming(
                    [sys.executable, "-m", "pipreqs.pipreqs", str(script_dir), "--force"],
                    cwd=str(script_dir),
                )
                if self.cancel_requested:
                    raise RuntimeError("Cancelled")
            else:
                if req_file.exists():
                    self._queue_log("Found existing requirements.txt in project directory.", "muted")
                else:
                    self._queue_log("Note: pipreqs not found. Proceeding with active environment.", "muted")

            # ---------------- Step 2: Install Dependencies --------
            if self.install_deps_var.get() and req_file.exists():
                self._queue_progress(20, "Installing dependencies…")
                self._queue_log("Step 2/4  →  Installing dependencies", "info")
                rc = self._run_streaming(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    cwd=str(script_dir),
                )
                if self.cancel_requested:
                    raise RuntimeError("Cancelled")
                if rc != 0:
                    self._queue_log("Dependency installation reported warnings or errors.", "warning")
            else:
                self._queue_progress(25, "Skipping dependency installation…")

            # ---------------- Step 3: PyInstaller Compilation ----
            self._queue_progress(35, "Compiling executable…")
            self._queue_log("Step 3/4  →  Compiling with PyInstaller", "info")

            for p in (temp_dist, temp_build):
                if p.exists():
                    shutil.rmtree(p, ignore_errors=True)

            cmd = [
                sys.executable,
                "-m",
                "PyInstaller",
                "--clean",
                "--noconfirm",
                f"--name={custom_name}",
                f"--workpath={temp_build}",
                f"--distpath={temp_dist}",
                f"--specpath={script_dir}",
            ]

            is_onefile = self.onefile_var.get()
            if is_onefile:
                cmd.append("--onefile")
            else:
                cmd.append("--onedir")

            if self.windowed_var.get():
                cmd.append("--windowed")

            if self.upx_var.get():
                cmd.append("--upx-dir=.")

            if icon_path and os.path.exists(icon_path):
                cmd.append(f"--icon={icon_path}")
                self._queue_log(f"Icon configured: {icon_path}", "muted")

            add_data_val = self.add_data_var.get().strip()
            if add_data_val:
                for entry in add_data_val.split(";"):
                    entry = entry.strip()
                    if entry:
                        cmd.append(f"--add-data={entry}")

            hidden_val = self.hidden_imports_var.get().strip()
            if hidden_val:
                for mod in hidden_val.replace(";", ",").split(","):
                    mod = mod.strip()
                    if mod:
                        cmd.append(f"--hidden-import={mod}")

            cmd.append(script_path)

            rc = self._run_streaming(cmd, cwd=str(script_dir))

            if self.cancel_requested:
                raise RuntimeError("Cancelled")
            if rc != 0:
                raise RuntimeError("PyInstaller build returned a non-zero exit code")

            # ---------------- Step 4: Finalize Output -------------
            self._queue_progress(85, "Finalizing output…")
            self._queue_log("Step 4/4  →  Moving executable & cleaning temporary files", "info")

            out_dir.mkdir(parents=True, exist_ok=True)
            ext = ".exe" if sys.platform == "win32" else ""

            if is_onefile:
                src_exe = temp_dist / f"{custom_name}{ext}"
                if not src_exe.exists():
                    possible = list(temp_dist.rglob(f"{custom_name}{ext}"))
                    if possible:
                        src_exe = possible[0]
                    else:
                        raise RuntimeError(f"Executable not found in {temp_dist}")

                dest_exe = out_dir / f"{custom_name}{ext}"
                if dest_exe.exists():
                    try:
                        dest_exe.unlink()
                    except Exception as e:
                        self._queue_log(f"Replacing existing file: {e}", "warning")

                shutil.move(str(src_exe), str(dest_exe))
            else:
                src_dir = temp_dist / custom_name
                dest_dir = out_dir / custom_name
                if not src_dir.exists():
                    possible_dirs = [d for d in temp_dist.iterdir() if d.is_dir()]
                    if possible_dirs:
                        src_dir = possible_dirs[0]
                    else:
                        raise RuntimeError("Directory output not found after onedir build")

                if dest_dir.exists():
                    shutil.rmtree(dest_dir, ignore_errors=True)

                shutil.move(str(src_dir), str(dest_dir))
                dest_exe = dest_dir / f"{custom_name}{ext}"

            # Clean temporary files safely
            for p in (temp_dist, temp_build):
                if p.exists():
                    shutil.rmtree(p, ignore_errors=True)

            if temp_spec.exists():
                try:
                    temp_spec.unlink()
                except Exception:
                    pass

            resolved_exe = str(dest_exe.resolve())
            self._queue_progress(100, "Build Complete")
            self._queue_log("✓  Build successful!", "success")
            self._queue_log(f"   Destination: {out_dir}", "success")
            self._queue_log(f"   Executable : {dest_exe.name}", "success")
            self._queue_finished("Build complete", success=True, exe_path=resolved_exe)

            if self.auto_run_var.get():
                self._queue_log("Launching executable…", "info")
                try:
                    subprocess.Popen([resolved_exe], cwd=str(dest_exe.parent))
                    self._queue_log("App launched.", "success")
                except Exception as e:
                    self._queue_log(f"Launch failed: {e}", "error")

        except RuntimeError as e:
            msg = str(e)
            if "Cancelled" in msg:
                self._queue_log("Build cancelled by user.", "warning")
                self._queue_finished("Cancelled", success=False)
            else:
                self._queue_log(f"Build failed: {msg}", "error")
                self._queue_finished("Failed", success=False)

            for p in (temp_dist, temp_build):
                if p.exists():
                    shutil.rmtree(p, ignore_errors=True)
            if temp_spec.exists():
                try:
                    temp_spec.unlink()
                except Exception:
                    pass

        except Exception as e:
            self._queue_log(f"Unexpected error: {e}", "error")
            self._queue_finished("Error", success=False)
            for p in (temp_dist, temp_build):
                if p.exists():
                    shutil.rmtree(p, ignore_errors=True)
            if temp_spec.exists():
                try:
                    temp_spec.unlink()
                except Exception:
                    pass

        finally:
            self.cfg.update({
                "output_dest": self.output_dest_var.get(),
                "onefile": self.onefile_var.get(),
                "windowed": self.windowed_var.get(),
                "upx": self.upx_var.get(),
                "auto_run": self.auto_run_var.get(),
                "install_deps": self.install_deps_var.get(),
                "custom_name": self.custom_name_var.get(),
                "add_data": self.add_data_var.get(),
                "hidden_imports": self.hidden_imports_var.get(),
                "geometry": self.geometry(),
            })
            save_config(self.cfg)

    def _on_close(self):
        if self.is_building:
            if messagebox.askyesno("Build running", "Cancel the current build and exit?"):
                self.cancel_build()
                self.after(500, self.destroy)
            return
        self.cfg["geometry"] = self.geometry()
        save_config(self.cfg)
        self.destroy()


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    app = AppBuilderGUI()
    app.mainloop()
