import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import configparser
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

CONFIG_FILE = "backup_config.ini"

DEFAULTS = {
    "source_path": "",
    "output_path": "",
    "winrar_path": "C:\\Program Files\\WinRAR\\Rar.exe",
    "archive_prefix": "GAME_BACKUP",
    "interval_minutes": "10",
    "max_archives": "0",
}

# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    cfg = configparser.ConfigParser()
    cfg["Settings"] = DEFAULTS.copy()
    if os.path.exists(CONFIG_FILE):
        cfg.read(CONFIG_FILE)
    return cfg["Settings"]

def save_config(values: dict):
    cfg = configparser.ConfigParser()
    cfg["Settings"] = values
    with open(CONFIG_FILE, "w") as f:
        cfg.write(f)

# ── Core backup logic ─────────────────────────────────────────────────────────

def get_archive_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0

def get_last_archive_size(output_path: str, prefix: str) -> int:
    try:
        files = sorted(
            [f for f in os.listdir(output_path) if f.startswith(prefix) and f.endswith(".rar")],
            reverse=True
        )
        if files:
            return get_archive_size(os.path.join(output_path, files[0]))
    except OSError:
        pass
    return 0

def prune_archives(output_path: str, prefix: str, max_archives: int, log):
    if max_archives <= 0:
        return
    try:
        files = sorted(
            [f for f in os.listdir(output_path) if f.startswith(prefix) and f.endswith(".rar")],
            reverse=True
        )
        if len(files) > max_archives:
            to_delete = files[max_archives:]
            for f in to_delete:
                full = os.path.join(output_path, f)
                os.remove(full)
                log(f"  [PRUNED] {f}")
    except OSError as e:
        log(f"  [ERROR] Pruning failed: {e}")

def run_backup(settings: dict, log, stop_event: threading.Event):
    source      = settings["source_path"]
    output      = settings["output_path"]
    winrar      = settings["winrar_path"]
    prefix      = settings["archive_prefix"]
    interval    = int(settings["interval_minutes"]) * 60
    max_arc     = int(settings["max_archives"])

    # Validate
    if not os.path.exists(winrar):
        log(f"[ERROR] WinRAR not found: {winrar}")
        return
    if not os.path.exists(source):
        log(f"[ERROR] Source folder not found: {source}")
        return
    os.makedirs(output, exist_ok=True)

    last_size = get_last_archive_size(output, prefix)
    log(f"Last backup size: {last_size} bytes")
    log("Backup loop started.\n")

    while not stop_event.is_set():
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        rar_name = f"{prefix}-{stamp}.rar"
        rar_path = os.path.join(output, rar_name)

        log(f"[{stamp}] Creating archive: {rar_name}")
        cmd = [winrar, "a", "-r", rar_path, source]
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=flags
        )
        # Stream WinRAR output line by line into the log as it happens
        for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line.strip():
                log(f"  {line}")
        process.wait()
        if process.returncode != 0:
            log(f"[{stamp}] [ERROR] WinRAR exited with code {process.returncode}")

        if not os.path.exists(rar_path):
            log(f"[{stamp}] [ERROR] Archive not created. WinRAR may have failed.")
        else:
            new_size = get_archive_size(rar_path)
            log(f"[{stamp}] New size : {new_size} bytes")
            log(f"[{stamp}] Last size: {last_size} bytes")

            if new_size == last_size:
                log(f"[{stamp}] No changes detected. Deleting redundant backup.")
                os.remove(rar_path)
            else:
                log(f"[{stamp}] Changes detected. Backup saved.")
                last_size = new_size

                if max_arc > 0:
                    log(f"[{stamp}] Pruning archives (max: {max_arc})...")
                    prune_archives(output, prefix, max_arc, log)

        # Countdown
        log("")
        log(f"Next backup in {interval // 60} minute(s)...")
        for remaining in range(interval, 0, -1):
            if stop_event.is_set():
                break
            time.sleep(1)

    log("")
    log("[STOPPED] Backup loop ended.")

# ── GUI ───────────────────────────────────────────────────────────────────────

class BackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Game Save Backup")
        self.resizable(False, False)
        self.config_data = load_config()
        self.stop_event = threading.Event()
        self.backup_thread = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ── Settings frame ────────────────────────────────────────────────────
        frm = tk.LabelFrame(self, text=" Settings ", font=("Segoe UI", 9, "bold"))
        frm.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")

        def row(label, key, browse=None, row=0):
            tk.Label(frm, text=label, anchor="w", width=18).grid(row=row, column=0, **pad, sticky="w")
            var = tk.StringVar(value=self.config_data.get(key, ""))
            entry = tk.Entry(frm, textvariable=var, width=52)
            entry.grid(row=row, column=1, **pad)
            if browse:
                tk.Button(frm, text="Browse…", command=lambda: self._browse(var, browse)).grid(
                    row=row, column=2, padx=(0, 8))
            return var

        self.v_source  = row("Source folder:",    "source_path",   "folder", row=0)
        self.v_output  = row("Output folder:",    "output_path",   "folder", row=1)
        self.v_winrar  = row("WinRAR path:",      "winrar_path",   "file",   row=2)
        self.v_prefix  = row("Archive prefix:",   "archive_prefix",          row=3)

        # Interval + max archives on same row
        num_frm = tk.Frame(frm)
        num_frm.grid(row=4, column=0, columnspan=3, sticky="w", **pad)

        tk.Label(num_frm, text="Interval (minutes):", anchor="w", width=18).pack(side="left")
        self.v_interval = tk.StringVar(value=self.config_data.get("interval_minutes", "10"))
        tk.Entry(num_frm, textvariable=self.v_interval, width=6).pack(side="left", padx=(0, 20))

        tk.Label(num_frm, text="Max archives (0 = unlimited):", anchor="w").pack(side="left")
        self.v_max = tk.StringVar(value=self.config_data.get("max_archives", "0"))
        tk.Entry(num_frm, textvariable=self.v_max, width=6).pack(side="left")

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frm = tk.Frame(self)
        btn_frm.grid(row=1, column=0, pady=4)

        self.btn_start = tk.Button(btn_frm, text="▶  Start Backup", width=18,
                                   bg="#2e7d32", fg="white", font=("Segoe UI", 9, "bold"),
                                   command=self._start)
        self.btn_start.pack(side="left", padx=6)

        self.btn_stop = tk.Button(btn_frm, text="■  Stop", width=12,
                                  bg="#c62828", fg="white", font=("Segoe UI", 9, "bold"),
                                  state="disabled", command=self._stop)
        self.btn_stop.pack(side="left", padx=6)

        tk.Button(btn_frm, text="Save Settings", width=14,
                  command=self._save_settings).pack(side="left", padx=6)

        tk.Button(btn_frm, text="Clear Log", width=10,
                  command=self._clear_log).pack(side="left", padx=6)

        # ── Log output ────────────────────────────────────────────────────────
        log_frm = tk.LabelFrame(self, text=" Log ", font=("Segoe UI", 9, "bold"))
        log_frm.grid(row=2, column=0, padx=12, pady=(4, 12), sticky="nsew")

        self.log_box = scrolledtext.ScrolledText(
            log_frm, width=90, height=22,
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white", state="disabled"
        )
        self.log_box.pack(padx=6, pady=6)

    def _browse(self, var: tk.StringVar, mode: str):
        if mode == "folder":
            path = filedialog.askdirectory(title="Select folder")
        else:
            path = filedialog.askopenfilename(title="Select WinRAR", filetypes=[("Executables", "*.exe")])
        if path:
            var.set(path.replace("/", "\\"))

    def _get_settings(self) -> dict:
        return {
            "source_path":      self.v_source.get().strip(),
            "output_path":      self.v_output.get().strip(),
            "winrar_path":      self.v_winrar.get().strip(),
            "archive_prefix":   self.v_prefix.get().strip(),
            "interval_minutes": self.v_interval.get().strip() or "10",
            "max_archives":     self.v_max.get().strip() or "0",
        }

    def _save_settings(self):
        save_config(self._get_settings())
        self._log("Settings saved.\n")

    def _validate(self, settings: dict) -> bool:
        try:
            val = int(settings["interval_minutes"])
            if val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Interval must be a positive whole number.")
            return False
        try:
            val = int(settings["max_archives"])
            if val < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Max archives must be 0 or a positive whole number.")
            return False
        if not settings["source_path"]:
            messagebox.showerror("Error", "Please set the source folder.")
            return False
        if not settings["output_path"]:
            messagebox.showerror("Error", "Please set the output folder.")
            return False
        if not settings["archive_prefix"].strip():
            messagebox.showerror("Error", "Please set an archive prefix.")
            return False
        return True

    def _start(self):
        settings = self._get_settings()
        if not self._validate(settings):
            return
        save_config(settings)
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._log("=== Backup started ===\n")
        self.backup_thread = threading.Thread(
            target=run_backup,
            args=(settings, self._log, self.stop_event),
            daemon=True
        )
        self.backup_thread.start()

    def _stop(self):
        self.stop_event.set()
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _log(self, msg: str):
        def _write():
            self.log_box.config(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _write)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")


if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()
