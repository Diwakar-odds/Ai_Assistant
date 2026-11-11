import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import threading
import json
import os
import shutil
import tempfile
from pathlib import Path
import subprocess
import sys

APP_NAME = "Pulsar AI Assistant"
APP_VERSION = "4.0.0"
PUBLISHER = "Pulsar AI Project"
UNINSTALL_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PulsarAssistant"
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "PulsarAIAssistant"
WEBVIEW2_CLIENT_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_DOWNLOAD_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_bundle_base() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent.parent.parent


def get_default_install_dir() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    return local_app_data / "Programs" / "PulsarAI"


def get_user_data_dir() -> Path:
    override = os.environ.get("PULSAR_DATA_DIR")
    if override and override.strip():
        return Path(override.strip()).expanduser().resolve()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    return local_app_data / "PulsarAI"


def check_webview2_available() -> tuple[bool, str]:
    """Check Microsoft Edge WebView2 Runtime availability via Registry & disk."""
    if sys.platform != "win32":
        return True, "Non-Windows environment"
    try:
        import winreg

        checks = [
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_GUID}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_GUID}"),
            (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_GUID}"),
        ]
        for hive, subkey in checks:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    pv, _ = winreg.QueryValueEx(key, "pv")
                    if pv and str(pv).strip() and str(pv).strip() != "0.0.0.0":
                        return True, f"v{str(pv).strip()}"
            except FileNotFoundError:
                continue
            except Exception:
                continue

        for base_env in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            root = os.environ.get(base_env)
            if root:
                wv_dir = Path(root) / "Microsoft" / "EdgeWebView" / "Application"
                if wv_dir.exists() and any(wv_dir.iterdir()):
                    return True, "Detected on disk"
    except Exception:
        return True, "Registry check skipped"
    return False, "Missing Microsoft Edge WebView2 Runtime"


def check_vcpp_runtime_available() -> bool:
    if sys.platform != "win32":
        return True
    sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    return (sys32 / "vcruntime140.dll").exists()


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Setup Wizard")
        self.geometry("680x520")
        self.resizable(False, False)

        self.base_path = get_bundle_base()
        self.user_data_dir = get_user_data_dir()
        self.install_dir = get_default_install_dir()
        self.webview2_ok = False
        self.webview2_info = "Pending check"
        self.install_error = None

        # Set window icon if present
        for icon_cand in (
            self.base_path / "icon.ico",
            self.base_path / "assets" / "icon.ico",
        ):
            if icon_cand.exists():
                try:
                    self.iconbitmap(str(icon_cand))
                    break
                except Exception:
                    pass

        # Configure clean Windows-native styling
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f4f6")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Header.TFrame", background="#0f172a")
        style.configure("TLabel", background="#f3f4f6", foreground="#111827", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#f3f4f6", foreground="#4b5563", font=("Segoe UI", 9))
        style.configure("BannerTitle.TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 14, "bold"))
        style.configure("BannerSub.TLabel", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("Section.TLabel", background="#f3f4f6", foreground="#0f172a", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 4))
        style.configure("TCheckbutton", background="#f3f4f6", font=("Segoe UI", 10))
        style.configure("TRadiobutton", background="#f3f4f6", font=("Segoe UI", 10))
        style.configure("Green.Horizontal.TProgressbar", background="#10b981", troughcolor="#e5e7eb")

        self.configure(bg="#f3f4f6")

        # Shared wizard variables
        self.eula_var = tk.BooleanVar(value=False)
        self.install_dir_var = tk.StringVar(value=str(self.install_dir))
        self.comp_core_var = tk.BooleanVar(value=True)
        self.comp_overlay_var = tk.BooleanVar(value=True)
        self.comp_desktop_shortcut_var = tk.BooleanVar(value=True)
        self.comp_start_menu_var = tk.BooleanVar(value=True)

        self.theme_var = tk.StringVar(value="dark")
        self.start_on_boot_var = tk.BooleanVar(value=True)
        self.hinglish_var = tk.BooleanVar(value=True)
        self.mic_var = tk.BooleanVar(value=True)
        self.notif_var = tk.BooleanVar(value=True)

        self.ai_provider_var = tk.StringVar(value="gemini")
        self.api_key_var = tk.StringVar(value="")
        self.show_key_var = tk.BooleanVar(value=False)

        self.launch_var = tk.BooleanVar(value=True)

        # Top Header Banner (Git-for-Windows style)
        self.banner_frame = ttk.Frame(self, style="Header.TFrame", padding=(20, 14))
        self.banner_frame.pack(side="top", fill="x")
        self.lbl_banner_title = ttk.Label(self.banner_frame, text=f"{APP_NAME} v{APP_VERSION}", style="BannerTitle.TLabel")
        self.lbl_banner_title.pack(anchor="w")
        self.lbl_banner_sub = ttk.Label(self.banner_frame, text="Production Desktop Setup Wizard", style="BannerSub.TLabel")
        self.lbl_banner_sub.pack(anchor="w", pady=(2, 0))

        # Bottom Navigation Bar
        self.nav_frame = ttk.Frame(self, padding=(20, 12))
        self.nav_frame.pack(side="bottom", fill="x")
        ttk.Separator(self, orient="horizontal").pack(side="bottom", fill="x")

        self.lbl_step_indicator = ttk.Label(self.nav_frame, text="Step 1 of 7", style="Muted.TLabel")
        self.lbl_step_indicator.pack(side="left")

        self.btn_cancel = ttk.Button(self.nav_frame, text="Cancel", command=self._confirm_cancel)
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_next = ttk.Button(self.nav_frame, text="Next >", command=self.next_step)
        self.btn_next.pack(side="right", padx=(8, 0))

        self.btn_back = ttk.Button(self.nav_frame, text="< Back", command=self.prev_step)
        self.btn_back.pack(side="right")

        # Main Page Container
        self.content_container = ttk.Frame(self, padding=(24, 16))
        self.content_container.pack(fill="both", expand=True)

        self.step_builders = [
            ("License Agreement", "Please review the EULA & privacy terms before continuing.", self.create_eula_page),
            ("Select Destination Location", f"Choose where {APP_NAME} should be installed.", self.create_destination_page),
            ("Select Components", "Choose which Pulsar components and shortcuts to install.", self.create_components_page),
            ("Additional Tasks", "Configure startup, theme, language, and system permissions.", self.create_tasks_page),
            ("AI Engine & API Key", "Select your default AI backend (Cloud or 100% Offline).", self.create_ai_config_page),
            ("Installing", f"Please wait while {APP_NAME} is installed and configured.", self.create_install_page),
            ("Completing Setup", f"{APP_NAME} is ready to use on your Windows PC.", self.create_finish_page),
        ]

        self.frames = []
        for _, _, builder in self.step_builders:
            frame = ttk.Frame(self.content_container)
            builder(frame)
            self.frames.append(frame)

        self.current_step = 0
        self.show_step(0)

    def _confirm_cancel(self):
        if messagebox.askyesno("Cancel Setup", f"Are you sure you want to exit {APP_NAME} Setup?"):
            self.destroy()

    def _load_license_text(self) -> str:
        candidates = [
            self.base_path / "docs" / "LICENSE.txt",
            self.base_path / "LICENSE.txt",
        ]
        for path in candidates:
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        return (
            "PULSAR AI ASSISTANT - END USER LICENSE & PRIVACY AGREEMENT\n\n"
            "1. PRIVACY & LOCAL STORAGE\n"
            "All user preferences, logs, conversation history, and Knowledge Graph data are stored\n"
            "locally on your machine under %LOCALAPPDATA%\\PulsarAI.\n\n"
            "2. CREDENTIALS & API KEYS\n"
            "Any third-party API keys (Google Gemini, OpenAI) you configure are stored using\n"
            "Windows Credential Manager / protected per-user files.\n\n"
            "3. MIT LICENSE & NO WARRANTY\n"
            "Permission is hereby granted, free of charge, under the MIT License.\n"
            "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND.\n"
        )

    def create_eula_page(self, parent):
        ttk.Label(parent, text="License Agreement & Privacy Guarantee", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        eula_text = tk.Text(
            text_frame,
            height=13,
            yscrollcommand=scrollbar.set,
            wrap="word",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#1f2937",
            padx=10,
            pady=8,
            relief="solid",
            borderwidth=1,
        )
        eula_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=eula_text.yview)

        eula_text.insert("1.0", self._load_license_text())
        eula_text.config(state="disabled")

        radio_frame = ttk.Frame(parent)
        radio_frame.pack(fill="x", pady=(12, 0))
        ttk.Radiobutton(
            radio_frame,
            text="I accept the agreement",
            variable=self.eula_var,
            value=True,
            command=self.update_nav,
        ).pack(anchor="w")
        ttk.Radiobutton(
            radio_frame,
            text="I do not accept the agreement",
            variable=self.eula_var,
            value=False,
            command=self.update_nav,
        ).pack(anchor="w", pady=(4, 0))

    def create_destination_page(self, parent):
        ttk.Label(parent, text="Where should Pulsar AI Assistant be installed?", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(
            parent,
            text=f"Setup will install {APP_NAME} into the following folder.\n"
                 "Installing under your User AppData Programs folder does not require Administrator elevation.",
            wraplength=600,
        ).pack(anchor="w", pady=(0, 14))

        dir_row = ttk.Frame(parent)
        dir_row.pack(fill="x", pady=(0, 10))
        self.entry_install_dir = ttk.Entry(dir_row, textvariable=self.install_dir_var, font=("Segoe UI", 10))
        self.entry_install_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(dir_row, text="Browse...", command=self._browse_install_dir).pack(side="right")

        self.lbl_space_info = ttk.Label(parent, text="", style="Muted.TLabel")
        self.lbl_space_info.pack(anchor="w", pady=(4, 16))
        self._refresh_disk_space()

        ttk.Label(
            parent,
            text=f"User preferences, logs & secure credentials will be stored safely at:\n{self.user_data_dir}",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=(8, 0))

    def _browse_install_dir(self):
        chosen = filedialog.askdirectory(
            title=f"Select {APP_NAME} Installation Folder",
            initialdir=str(self.install_dir.parent if self.install_dir.parent.exists() else Path.home()),
        )
        if chosen:
            chosen_path = Path(chosen)
            if chosen_path.name.lower() != "pulsarai":
                chosen_path = chosen_path / "PulsarAI"
            self.install_dir_var.set(str(chosen_path))
            self._refresh_disk_space()

    def _refresh_disk_space(self):
        try:
            target = Path(self.install_dir_var.get().strip() or str(self.install_dir))
            probe = target
            while not probe.exists() and probe.parent != probe:
                probe = probe.parent
            usage = shutil.disk_usage(probe)
            free_gb = usage.free / (1024 ** 3)
            self.lbl_space_info.config(text=f"Available disk space on target drive: {free_gb:.1f} GB (At least 500 MB recommended)")
        except Exception:
            self.lbl_space_info.config(text="At least 500 MB of free disk space is recommended.")

    def create_components_page(self, parent):
        ttk.Label(parent, text="Select Components to Install", style="Section.TLabel").pack(anchor="w", pady=(0, 10))

        core_cb = ttk.Checkbutton(
            parent,
            text=f"{APP_NAME} Core & Edge WebView2 Desktop UI (Required)",
            variable=self.comp_core_var,
        )
        core_cb.state(["disabled", "selected"])
        core_cb.pack(anchor="w", pady=5)

        ttk.Checkbutton(
            parent,
            text="Floating 4D Orb Desktop Overlay & Wake-Word Listener",
            variable=self.comp_overlay_var,
        ).pack(anchor="w", pady=5)

        ttk.Checkbutton(
            parent,
            text="Create a Desktop shortcut",
            variable=self.comp_desktop_shortcut_var,
        ).pack(anchor="w", pady=5)

        ttk.Checkbutton(
            parent,
            text="Create Start Menu Programs shortcuts (App + Uninstaller)",
            variable=self.comp_start_menu_var,
        ).pack(anchor="w", pady=5)

    def create_tasks_page(self, parent):
        ttk.Label(parent, text="Appearance & System Behavior", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        theme_box = ttk.Frame(parent)
        theme_box.pack(fill="x", pady=(0, 12))
        ttk.Label(theme_box, text="Default UI Theme:").pack(anchor="w", pady=(0, 4))
        ttk.Radiobutton(theme_box, text="Dark Mode (Recommended)", variable=self.theme_var, value="dark").pack(anchor="w", padx=16)
        ttk.Radiobutton(theme_box, text="Light Mode", variable=self.theme_var, value="light").pack(anchor="w", padx=16, pady=(2, 0))

        ttk.Label(parent, text="Additional System Tasks:", style="Section.TLabel").pack(anchor="w", pady=(6, 6))
        ttk.Checkbutton(parent, text="Start Pulsar AI automatically when I sign in to Windows", variable=self.start_on_boot_var).pack(anchor="w", pady=4)
        ttk.Checkbutton(parent, text="Enable Hinglish (Hindi + English) bilingual command mode", variable=self.hinglish_var).pack(anchor="w", pady=4)
        ttk.Checkbutton(parent, text="Enable Microphone & Voice Assistant features", variable=self.mic_var).pack(anchor="w", pady=4)
        ttk.Checkbutton(parent, text="Enable Desktop Notifications", variable=self.notif_var).pack(anchor="w", pady=4)

    def create_ai_config_page(self, parent):
        ttk.Label(parent, text="Choose Default AI Backend", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(
            parent,
            text="You can switch between Cloud and Local AI anytime inside Pulsar Settings.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        ttk.Radiobutton(
            parent,
            text="Google Gemini (Cloud AI — Fast & Multilingual, Recommended)",
            variable=self.ai_provider_var,
            value="gemini",
            command=self._toggle_api_key_state,
        ).pack(anchor="w", pady=4)
        ttk.Radiobutton(
            parent,
            text="OpenAI GPT (Cloud AI — gpt-4o-mini / gpt-4o)",
            variable=self.ai_provider_var,
            value="openai",
            command=self._toggle_api_key_state,
        ).pack(anchor="w", pady=4)
        ttk.Radiobutton(
            parent,
            text="Local / Offline Mode (Built-in Pulsar GGUF — Zero Cloud Calls)",
            variable=self.ai_provider_var,
            value="gguf",
            command=self._toggle_api_key_state,
        ).pack(anchor="w", pady=4)

        key_frame = ttk.Frame(parent)
        key_frame.pack(fill="x", pady=(14, 0))
        self.lbl_api_prompt = ttk.Label(key_frame, text="API Key (Optional — leave blank to configure later):")
        self.lbl_api_prompt.pack(anchor="w", pady=(0, 4))

        entry_row = ttk.Frame(key_frame)
        entry_row.pack(fill="x")
        self.entry_api_key = ttk.Entry(entry_row, textvariable=self.api_key_var, show="*", font=("Segoe UI", 10))
        self.entry_api_key.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Checkbutton(entry_row, text="Show", variable=self.show_key_var, command=self._toggle_show_key).pack(side="right")

        ttk.Label(
            parent,
            text="Security Note: Keys entered here are stored in Windows Credential Manager (never plaintext JSON).",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=(8, 0))
        self._toggle_api_key_state()

    def _toggle_show_key(self):
        if self.ai_provider_var.get() in ("gemini", "openai"):
            self.entry_api_key.config(show="" if self.show_key_var.get() else "*")

    def _toggle_api_key_state(self):
        prov = self.ai_provider_var.get()
        if prov in ("gemini", "openai"):
            self.entry_api_key.config(state="normal")
            label = "Google Gemini API Key (Optional):" if prov == "gemini" else "OpenAI API Key (Optional):"
            self.lbl_api_prompt.config(text=label)
        else:
            self.entry_api_key.config(state="disabled")
            self.lbl_api_prompt.config(text="API Key not required in Local/Offline mode.")

    def create_install_page(self, parent):
        ttk.Label(parent, text="Installing Pulsar AI Assistant", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.lbl_progress = ttk.Label(parent, text="Preparing installation...")
        self.lbl_progress.pack(anchor="w", pady=(0, 8))

        self.progress = ttk.Progressbar(
            parent, style="Green.Horizontal.TProgressbar", orient="horizontal", length=620, mode="determinate"
        )
        self.progress.pack(fill="x", pady=(0, 10))

        self.install_log = tk.Text(
            parent,
            height=12,
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#e2e8f0",
            relief="solid",
            borderwidth=1,
            state="disabled",
            padx=8,
            pady=6,
        )
        self.install_log.pack(fill="both", expand=True)

    def create_finish_page(self, parent):
        ttk.Label(parent, text=f"Completing the {APP_NAME} Setup Wizard", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.lbl_finish_summary = ttk.Label(
            parent,
            text=f"{APP_NAME} has been installed on your computer.",
            wraplength=600,
            justify="left",
        )
        self.lbl_finish_summary.pack(anchor="w", pady=(0, 16))

        ttk.Checkbutton(parent, text=f"Launch {APP_NAME}", variable=self.launch_var).pack(anchor="w", pady=8)

        self.lbl_webview_warning = ttk.Label(
            parent,
            text="",
            foreground="#b45309",
            wraplength=600,
        )
        self.lbl_webview_warning.pack(anchor="w", pady=(10, 0))

    def _log(self, msg: str):
        def _append():
            self.install_log.config(state="normal")
            self.install_log.insert("end", msg + "\n")
            self.install_log.see("end")
            self.install_log.config(state="disabled")

        self.after(0, _append)

    def show_step(self, step: int):
        for frame in self.frames:
            frame.pack_forget()

        title, sub, _ = self.step_builders[step]
        self.lbl_banner_title.config(text=f"{APP_NAME} — {title}")
        self.lbl_banner_sub.config(text=sub)
        self.lbl_step_indicator.config(text=f"Step {step + 1} of {len(self.step_builders)}")

        self.frames[step].pack(fill="both", expand=True)
        self.current_step = step
        self.update_nav()

        if step == 1:
            self._refresh_disk_space()

        if step == 5:  # Installing page
            self.install_dir = Path(self.install_dir_var.get().strip() or str(get_default_install_dir())).expanduser()
            self.btn_next.config(state="disabled")
            self.btn_back.config(state="disabled")
            self.btn_cancel.config(state="disabled")
            threading.Thread(target=self.run_installation, daemon=True).start()

        if step == 6:  # Finish page
            self.btn_next.config(state="normal", text="Finish")
            self.btn_back.config(state="disabled")
            self.btn_cancel.pack_forget()
            summary = (
                f"Setup has finished installing {APP_NAME} on your computer.\n\n"
                f"• Installation Folder: {self.install_dir}\n"
                f"• User Data & Logs: {self.user_data_dir}\n"
                f"• Edge WebView2 Runtime: {self.webview2_info}\n"
                f"• Default AI Provider: {self.ai_provider_var.get().upper()}"
            )
            self.lbl_finish_summary.config(text=summary)
            if not self.webview2_ok:
                self.lbl_webview_warning.config(
                    text="Note: Microsoft Edge WebView2 Runtime was not detected. "
                         "If the app prompts on first launch, allow it to install WebView2 Runtime."
                )

    def update_nav(self):
        if self.current_step == 0:
            self.btn_back.config(state="disabled")
            self.btn_next.config(state="normal" if self.eula_var.get() else "disabled", text="Next >")
        elif self.current_step in (1, 2, 3):
            self.btn_back.config(state="normal")
            self.btn_next.config(state="normal", text="Next >")
        elif self.current_step == 4:
            self.btn_back.config(state="normal")
            self.btn_next.config(state="normal", text="Install")
        elif self.current_step == 6:
            self.btn_back.config(state="disabled")
            self.btn_next.config(state="normal", text="Finish")

    def next_step(self):
        if self.current_step == 1:
            raw_dir = self.install_dir_var.get().strip()
            if not raw_dir:
                messagebox.showerror("Invalid Folder", "Please specify an installation folder.")
                return
            self.install_dir = Path(raw_dir).expanduser()
        if self.current_step == 6:
            self.finish_setup()
        elif self.current_step < len(self.step_builders) - 1:
            self.show_step(self.current_step + 1)

    def prev_step(self):
        if self.current_step > 0 and self.current_step != 5:
            self.show_step(self.current_step - 1)

    def _set_progress(self, pct: int, label: str):
        def _upd():
            self.progress["value"] = pct
            self.lbl_progress.config(text=label)

        self.after(0, _upd)

    def run_installation(self):
        try:
            self._set_progress(8, "Checking Windows prerequisites (Edge WebView2 & VC++)...")
            self.webview2_ok, self.webview2_info = check_webview2_available()
            vcpp_ok = check_vcpp_runtime_available()
            self._log(f"[CHECK] Edge WebView2 Runtime: {'OK (' + self.webview2_info + ')' if self.webview2_ok else 'NOT DETECTED'}")
            self._log(f"[CHECK] Visual C++ Runtime: {'OK' if vcpp_ok else 'WARNING (vcruntime140.dll missing)'}")

            self._set_progress(22, "Preparing destination folder...")
            self.install_dir.mkdir(parents=True, exist_ok=True)
            self._log(f"[DIR] Install path: {self.install_dir}")

            # Close running app instance before overwriting binaries
            target_exe = self.install_dir / "Pulsar_AI_Assistant.exe"
            if sys.platform == "win32" and target_exe.exists():
                subprocess.run(
                    ["taskkill", "/F", "/IM", "Pulsar_AI_Assistant.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                time.sleep(0.4)

            self._set_progress(45, "Extracting application binaries & assets...")
            self.extract_app()

            self._set_progress(68, "Saving user preferences & credentials...")
            self.save_settings()

            self._set_progress(84, "Creating shortcuts & Windows registry entries...")
            self.create_shortcuts()
            self.register_uninstaller()
            self.sync_startup_registry()

            self._set_progress(100, "Installation completed successfully!")
            self._log("[DONE] Setup completed successfully.")
            time.sleep(0.4)
            self.after(0, lambda: self.show_step(6))
        except Exception as e:
            self.install_error = str(e)
            self._log(f"[ERROR] Installation failed: {e}")
            self.after(0, lambda: messagebox.showerror("Installation Error", f"Setup encountered an error:\n{e}"))

    def extract_app(self):
        # 1. Bundled onedir folder (preferred modern distribution)
        bundled_dirs = [
            self.base_path / "Pulsar_AI_Assistant",
            self.base_path / "dist_package" / "Pulsar_AI_Assistant",
        ]
        src_dir = next((d for d in bundled_dirs if d.exists() and d.is_dir()), None)

        if src_dir is not None:
            self._log(f"[COPY] Copying {src_dir.name} to {self.install_dir}...")
            shutil.copytree(src_dir, self.install_dir, dirs_exist_ok=True)
        else:
            bundled_exes = [
                self.base_path / "Pulsar_AI_Assistant.exe",
                self.base_path / "Pulsar_Assistant.exe",
            ]
            src_exe = next((p for p in bundled_exes if p.exists()), None)
            if src_exe is not None:
                self._log(f"[COPY] Copying {src_exe.name}...")
                shutil.copy2(src_exe, self.install_dir / "Pulsar_AI_Assistant.exe")
            else:
                self._log("[DEV] Bundled .exe payload not present (source checkout mode) — configuring metadata only.")

        # 2. Uninstaller
        for uninst_cand in (
            self.base_path / "Uninstall_Pulsar.exe",
            self.base_path / "dist_package" / "Uninstall_Pulsar.exe",
        ):
            if uninst_cand.exists():
                shutil.copy2(uninst_cand, self.install_dir / "Uninstall_Pulsar.exe")
                self._log("[COPY] Installed Uninstall_Pulsar.exe")
                break

        # 3. Icon & License
        for icon_cand in (self.base_path / "icon.ico", self.base_path / "assets" / "icon.ico"):
            if icon_cand.exists():
                shutil.copy2(icon_cand, self.install_dir / "icon.ico")
                break

        for lic_cand in (self.base_path / "LICENSE.txt", self.base_path / "docs" / "LICENSE.txt"):
            if lic_cand.exists():
                shutil.copy2(lic_cand, self.install_dir / "LICENSE.txt")
                break

    def _create_windows_lnk(self, link_path: Path, target_path: Path, working_dir: Path, icon_path: Path, description: str = ""):
        link_path.parent.mkdir(parents=True, exist_ok=True)
        esc = lambda s: str(s).replace('"', '""')
        icon_line = f'oLink.IconLocation = "{esc(icon_path)}"' if icon_path.exists() else ""
        desc_line = f'oLink.Description = "{esc(description)}"' if description else ""
        vbs_script = (
            'Set oWS = WScript.CreateObject("WScript.Shell")\n'
            f'Set oLink = oWS.CreateShortcut("{esc(link_path)}")\n'
            f'oLink.TargetPath = "{esc(target_path)}"\n'
            f'oLink.WorkingDirectory = "{esc(working_dir)}"\n'
            f"{icon_line}\n"
            f"{desc_line}\n"
            "oLink.Save\n"
        )
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".vbs", encoding="utf-8") as vbs:
            vbs.write(vbs_script)
            vbs_path = vbs.name
        try:
            subprocess.run(
                ["cscript.exe", "//Nologo", vbs_path],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        finally:
            try:
                os.remove(vbs_path)
            except Exception:
                pass

    def create_shortcuts(self):
        target_exe = self.install_dir / "Pulsar_AI_Assistant.exe"
        icon_path = self.install_dir / "icon.ico"
        uninstall_exe = self.install_dir / "Uninstall_Pulsar.exe"

        if not target_exe.exists() or sys.platform != "win32":
            self._log("[SHORTCUT] Executable not present on disk; skipping .lnk creation.")
            return

        if self.comp_desktop_shortcut_var.get():
            desktop_link = Path(os.path.expanduser("~/Desktop")) / "Pulsar AI Assistant.lnk"
            self._create_windows_lnk(
                desktop_link, target_exe, self.install_dir, icon_path, "Launch Pulsar AI Assistant"
            )
            self._log(f"[SHORTCUT] Desktop shortcut created: {desktop_link.name}")

        if self.comp_start_menu_var.get():
            appdata = Path(os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming")))
            sm_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
            self._create_windows_lnk(
                sm_dir / "Pulsar AI Assistant.lnk", target_exe, self.install_dir, icon_path, "Launch Pulsar AI Assistant"
            )
            if uninstall_exe.exists():
                self._create_windows_lnk(
                    sm_dir / "Uninstall Pulsar AI.lnk", uninstall_exe, self.install_dir, icon_path, "Uninstall Pulsar AI Assistant"
                )
            self._log(f"[SHORTCUT] Start Menu folder created: {sm_dir}")

    def _estimate_install_size_kb(self) -> int:
        try:
            total = sum(p.stat().st_size for p in self.install_dir.rglob("*") if p.is_file())
            return max(1024, int(total // 1024))
        except Exception:
            return 250000

    def register_uninstaller(self):
        """Register app in Windows Installed Apps (Add/Remove Programs)."""
        if sys.platform != "win32":
            return
        try:
            import winreg

            uninstall_exe = self.install_dir / "Uninstall_Pulsar.exe"
            icon_path = self.install_dir / "icon.ico"

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_KEY) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}"')
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.install_dir))
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
                winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, self._estimate_install_size_kb())
                if icon_path.exists():
                    winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(icon_path))
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            self._log("[REGISTRY] Registered in Windows Add/Remove Programs.")
        except Exception as e:
            self._log(f"[WARN] Registry registration skipped: {e}")

    def sync_startup_registry(self):
        if sys.platform != "win32":
            return
        target_exe = self.install_dir / "Pulsar_AI_Assistant.exe"
        if not target_exe.exists():
            return
        try:
            import winreg

            if self.start_on_boot_var.get():
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY) as key:
                    winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, f'"{target_exe}"')
                self._log("[STARTUP] Auto-start with Windows enabled.")
            else:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, STARTUP_VALUE_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            self._log(f"[WARN] Startup registry sync skipped: {e}")

    def _store_api_key(self, provider: str, key_value: str) -> str:
        """Persist optional API key in Windows Credential Manager (never plaintext JSON)."""
        val = (key_value or "").strip()
        if not val:
            return ""
        keyring_map = {"gemini": "googleGemini", "openai": "openAI"}
        kr_name = keyring_map.get(provider)
        if not kr_name:
            return ""
        try:
            import keyring

            keyring.set_password("Pulsar_Assistant", kr_name, val)
            self._log(f"[KEYRING] Stored {provider} API key securely in Windows Credential Manager.")
            return "********"
        except Exception as e:
            # Fallback to per-user AppData .env if keyring backend unavailable
            try:
                env_var = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
                env_file = self.user_data_dir / ".env"
                env_file.parent.mkdir(parents=True, exist_ok=True)
                lines = []
                if env_file.exists():
                    lines = [ln for ln in env_file.read_text(encoding="utf-8").splitlines() if not ln.startswith(f"{env_var}=")]
                lines.append(f"{env_var}={val}")
                env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
                self._log(f"[ENV] Saved {env_var} to protected per-user .env ({e})")
            except Exception:
                pass
            return "********"

    def save_settings(self):
        settings_file = self.user_data_dir / "data" / "user_preferences" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)

        existing = {}
        if settings_file.exists():
            try:
                existing = json.loads(settings_file.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                existing = {}

        provider = self.ai_provider_var.get()
        model_map = {
            "gemini": "gemini-2.5-flash",
            "openai": "gpt-4o-mini",
            "gguf": "pulsar-final-q4_k_m",
        }

        key_mask = self._store_api_key(provider, self.api_key_var.get())
        key_field = "googleGemini" if provider == "gemini" else ("openAI" if provider == "openai" else None)

        existing["onboarded"] = True
        existing["installer_completed"] = True

        gen = existing.setdefault("general", {})
        gen["theme"] = self.theme_var.get()
        gen["startOnBoot"] = bool(self.start_on_boot_var.get())
        gen["enableHinglish"] = bool(self.hinglish_var.get())

        ai_cfg = existing.setdefault("ai", {})
        ai_cfg["defaultProvider"] = provider
        ai_cfg["defaultModel"] = model_map.get(provider, "gemini-2.5-flash")

        voice_cfg = existing.setdefault("voice", {})
        stt_cfg = voice_cfg.setdefault("stt", {})
        stt_cfg["enabled"] = bool(self.mic_var.get())

        sys_cfg = existing.setdefault("system", {})
        sys_cfg["desktopOverlay"] = bool(self.comp_overlay_var.get())
        notif_cfg = sys_cfg.setdefault("notifications", {})
        notif_cfg["desktop"] = bool(self.notif_var.get())

        if key_field and key_mask:
            sec = existing.setdefault("security", {})
            api_keys = sec.setdefault("apiKeys", {})
            api_keys[key_field] = key_mask

        settings_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        self._log(f"[CONFIG] Initialized unified preferences: {settings_file}")

    def finish_setup(self):
        if self.launch_var.get():
            target_exe = self.install_dir / "Pulsar_AI_Assistant.exe"
            if target_exe.exists():
                subprocess.Popen([str(target_exe)], cwd=str(target_exe.parent))
            else:
                dev_launcher = self.base_path / "desktop" / "app_launcher.py"
                if dev_launcher.exists():
                    subprocess.Popen([sys.executable, str(dev_launcher)], cwd=str(self.base_path))
        self.destroy()


if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
