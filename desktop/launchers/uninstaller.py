import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
import sys

APP_NAME = "Pulsar AI Assistant"
UNINSTALL_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PulsarAssistant"
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "PulsarAIAssistant"


def discover_install_dir() -> Path:
    """Resolve real InstallLocation from Registry, falling back to default user path."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_KEY) as key:
                loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                if loc and Path(loc).exists():
                    return Path(loc)
        except Exception:
            pass

    local_app_data = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    for candidate in (
        local_app_data / "Programs" / "PulsarAI",
        local_app_data / "Pulsar_Assistant",
    ):
        if candidate.exists():
            return candidate
    return local_app_data / "Programs" / "PulsarAI"


def get_user_data_dir() -> Path:
    override = os.environ.get("PULSAR_DATA_DIR")
    if override and override.strip():
        return Path(override.strip()).expanduser().resolve()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    return local_app_data / "PulsarAI"


class UninstallWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Uninstall")
        self.geometry("500x360")
        self.resizable(False, False)

        self.install_dir = discover_install_dir()
        self.user_data_dir = get_user_data_dir()
        self.remove_user_data_var = tk.BooleanVar(value=False)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f4f6")
        style.configure("TLabel", background="#f3f4f6", foreground="#111827", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", foreground="#4b5563", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background="#f3f4f6", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 4))
        style.configure("Red.Horizontal.TProgressbar", background="#dc2626")
        self.configure(bg="#f3f4f6")

        self.main_frame = ttk.Frame(self, padding=(28, 20))
        self.main_frame.pack(fill="both", expand=True)

        ttk.Label(self.main_frame, text=f"Uninstall {APP_NAME}", style="Header.TLabel").pack(anchor="w", pady=(0, 12))

        ttk.Label(
            self.main_frame,
            text=f"This will remove {APP_NAME}, its Desktop & Start Menu shortcuts,\n"
                 f"and Windows startup configuration.\n\n"
                 f"Install Folder: {self.install_dir}",
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(0, 12))

        ttk.Checkbutton(
            self.main_frame,
            text=f"Also delete personal settings, logs & Knowledge Graph\n({self.user_data_dir})",
            variable=self.remove_user_data_var,
        ).pack(anchor="w", pady=(4, 14))

        self.progress = ttk.Progressbar(
            self.main_frame,
            style="Red.Horizontal.TProgressbar",
            orient="horizontal",
            length=440,
            mode="determinate",
        )
        self.status_label = ttk.Label(self.main_frame, text="", style="Muted.TLabel")

        btn_frame = ttk.Frame(self, padding=(20, 12))
        btn_frame.pack(side="bottom", fill="x")
        ttk.Separator(self, orient="horizontal").pack(side="bottom", fill="x")

        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_uninstall = ttk.Button(btn_frame, text="Uninstall", command=self.start_uninstall)
        self.btn_uninstall.pack(side="right")

    def start_uninstall(self):
        confirm = messagebox.askyesno(
            "Confirm Uninstall",
            f"Are you sure you want to remove {APP_NAME} from your computer?",
        )
        if not confirm:
            return

        self.btn_uninstall.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        self.progress.pack(fill="x", pady=(4, 6))
        self.status_label.pack(anchor="w")

        threading.Thread(target=self.run_uninstall, daemon=True).start()

    def _set_status(self, pct: int, msg: str):
        def _upd():
            self.progress["value"] = pct
            self.status_label.config(text=msg)

        self.after(0, _upd)

    def run_uninstall(self):
        steps = [
            (20, "Stopping running Pulsar processes...", self.stop_running_processes),
            (40, "Removing Desktop & Start Menu shortcuts...", self.remove_shortcuts),
            (65, "Cleaning up Windows Registry entries...", self.cleanup_registry),
            (88, "Removing application files...", self.remove_app_files),
        ]
        if self.remove_user_data_var.get():
            steps.append((95, "Removing personal AppData & Knowledge Graph...", self.remove_user_data))

        for pct, label, action in steps:
            self._set_status(pct, label)
            try:
                action()
            except Exception as e:
                print(f"Uninstall step failed: {e}")
            time.sleep(0.25)

        self._set_status(100, "Uninstallation complete.")
        self.after(0, self._finish_dialog)

    def _finish_dialog(self):
        messagebox.showinfo(
            "Uninstall Complete",
            f"{APP_NAME} has been successfully removed from your computer.",
        )
        # If running from inside install_dir as a frozen exe, schedule deferred cleanup of self
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            try:
                exe_path = Path(sys.executable).resolve()
                if self.install_dir.exists() and (
                    exe_path.parent == self.install_dir or self.install_dir in exe_path.parents
                ):
                    cmd = f'ping 127.0.0.1 -n 3 > nul & rd /s /q "{self.install_dir}"'
                    subprocess.Popen(
                        ["cmd.exe", "/c", cmd],
                        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    )
            except Exception:
                pass
        self.destroy()

    def stop_running_processes(self):
        if sys.platform != "win32":
            return
        for proc_name in ("Pulsar_AI_Assistant.exe", "Pulsar_Assistant.exe"):
            subprocess.run(
                ["taskkill", "/F", "/IM", proc_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    def remove_shortcuts(self):
        desktop = Path(os.path.expanduser("~/Desktop"))
        for lnk_name in ("Pulsar AI Assistant.lnk", "Pulsar Assistant.lnk"):
            lnk = desktop / lnk_name
            if lnk.exists():
                lnk.unlink()

        appdata = Path(os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming")))
        sm_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
        if sm_dir.exists():
            shutil.rmtree(sm_dir, ignore_errors=True)

    def remove_app_files(self):
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)

    def remove_user_data(self):
        if self.user_data_dir.exists():
            shutil.rmtree(self.user_data_dir, ignore_errors=True)

    def cleanup_registry(self):
        if sys.platform != "win32":
            return
        import winreg

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_KEY)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Uninstall registry cleanup note: {e}")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Startup registry cleanup note: {e}")


if __name__ == "__main__":
    app = UninstallWizard()
    app.mainloop()
