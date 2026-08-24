import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import json
import os
from pathlib import Path
import subprocess
import sys

class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pulsar Assistant - Setup")
        self.geometry("600x450")
        self.resizable(False, False)
        
        # Determine paths
        try:
            self.base_path = Path(sys._MEIPASS)
        except Exception:
            self.base_path = Path(__file__).parent.parent.parent.parent

        self.settings_path = self.base_path / "config" / "user_settings.json"
        
        # Configure style
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Green.Horizontal.TProgressbar', background='#28a745')

        self.configure(bg='#f0f0f0')
        
        self.current_step = 0
        self.steps = [
            self.create_welcome_page,
            self.create_theme_page,
            self.create_permissions_page,
            self.create_install_page,
            self.create_finish_page
        ]
        
        self.frames = []
        for step in self.steps:
            frame = ttk.Frame(self)
            self.frames.append(frame)
            step(frame)
            
        # Bottom Navigation Bar
        self.nav_frame = ttk.Frame(self)
        self.nav_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        
        ttk.Separator(self, orient='horizontal').pack(side="bottom", fill="x", pady=5)
        
        self.btn_back = ttk.Button(self.nav_frame, text="< Back", command=self.prev_step)
        self.btn_back.pack(side="left")
        
        self.btn_next = ttk.Button(self.nav_frame, text="Next >", command=self.next_step)
        self.btn_next.pack(side="right")
        
        self.btn_cancel = ttk.Button(self.nav_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=10)
        
        self.show_step(0)

    def create_welcome_page(self, parent):
        ttk.Label(parent, text="Welcome to Pulsar Setup", style='Header.TLabel').pack(pady=10)
        ttk.Label(parent, text="Please read the following End User License Agreement:").pack(pady=(0, 5))
        
        # Add scrollable text area for EULA
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        eula_text = tk.Text(text_frame, height=10, width=50, yscrollcommand=scrollbar.set, wrap="word", font=('Segoe UI', 9))
        eula_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=eula_text.yview)
        
        agreement = (
            "END USER LICENSE AGREEMENT (EULA)\n\n"
            "Please read this agreement carefully before installing Pulsar AI Assistant.\n\n"
            "1. PRIVACY & DATA\n"
            "This application processes and stores your data locally. By using the voice assistant, "
            "you agree that voice data is captured by your microphone and processed using local models. "
            "No data is sent to external servers without your explicit action.\n\n"
            "2. LOCAL KNOWLEDGE GRAPH\n"
            "The assistant builds a local Knowledge Graph based on your interactions to personalize your experience. "
            "This data remains strictly on your local machine.\n\n"
            "3. NO WARRANTY\n"
            "This software is provided 'as-is' without any warranty. The developer is not responsible for any issues "
            "arising from its use.\n\n"
            "By checking the box below, you agree to these terms."
        )
        eula_text.insert("1.0", agreement)
        eula_text.config(state="disabled") # Make it read-only
        
        self.eula_var = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(parent, text="I accept the agreement", variable=self.eula_var, command=self.update_nav)
        cb.pack(pady=(10, 20))

    def create_theme_page(self, parent):
        ttk.Label(parent, text="Select Your Theme", style='Header.TLabel').pack(pady=20)
        ttk.Label(parent, text="Choose how you want the application to look:").pack(pady=10)
        
        self.theme_var = tk.StringVar(value="Dark")
        ttk.Radiobutton(parent, text="Dark Mode (Recommended)", variable=self.theme_var, value="Dark").pack(pady=5)
        ttk.Radiobutton(parent, text="Light Mode", variable=self.theme_var, value="Light").pack(pady=5)

    def create_permissions_page(self, parent):
        ttk.Label(parent, text="System Permissions", style='Header.TLabel').pack(pady=20)
        text = (
            "Pulsar Assistant is voice-first. We need permission to use your microphone.\n"
            "We also need permission to send Desktop Notifications."
        )
        ttk.Label(parent, text=text, justify="center", wraplength=500).pack(pady=20)
        
        self.mic_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Allow Microphone Access", variable=self.mic_var).pack(pady=5)
        
        self.notif_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Allow Desktop Notifications", variable=self.notif_var).pack(pady=5)

    def create_install_page(self, parent):
        ttk.Label(parent, text="Installing...", style='Header.TLabel').pack(pady=20)
        self.lbl_progress = ttk.Label(parent, text="Preparing to install...")
        self.lbl_progress.pack(pady=10)
        
        self.progress = ttk.Progressbar(parent, style='Green.Horizontal.TProgressbar', orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=20)

    def create_finish_page(self, parent):
        ttk.Label(parent, text="Installation Complete", style='Header.TLabel').pack(pady=20)
        ttk.Label(parent, text="Pulsar Assistant has been successfully installed on your computer.").pack(pady=20)
        self.launch_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Launch Pulsar Assistant", variable=self.launch_var).pack(pady=20)

    def show_step(self, step):
        for frame in self.frames:
            frame.pack_forget()
        
        self.frames[step].pack(fill="both", expand=True)
        self.current_step = step
        self.update_nav()
        
        if step == 3: # Install page
            self.btn_next.config(state="disabled")
            self.btn_back.config(state="disabled")
            self.btn_cancel.config(state="disabled")
            threading.Thread(target=self.run_installation, daemon=True).start()
            
        if step == 4: # Finish page
            self.btn_next.config(text="Finish")
            self.btn_back.config(state="disabled")
            self.btn_cancel.pack_forget()

    def update_nav(self):
        if self.current_step == 0:
            self.btn_back.config(state="disabled")
            self.btn_next.config(state="normal" if self.eula_var.get() else "disabled")
            self.btn_next.config(text="Next >")
        elif self.current_step in [1, 2]:
            self.btn_back.config(state="normal")
            self.btn_next.config(state="normal")
            self.btn_next.config(text="Next >" if self.current_step == 1 else "Install")
        elif self.current_step == 4:
            self.btn_next.config(state="normal", text="Finish")
            
    def next_step(self):
        if self.current_step == 4:
            self.finish_setup()
        elif self.current_step < len(self.steps) - 1:
            self.show_step(self.current_step + 1)
            
    def prev_step(self):
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def run_installation(self):
        # Simulate installation process
        tasks = [
            "Extracting files...",
            "Setting up local Knowledge Graph...",
            "Applying Theme preferences...",
            "Configuring Permissions...",
            "Creating Desktop Shortcuts...",
            "Finalizing setup..."
        ]
        
        # Determine installation directory
        local_app_data = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
        self.install_dir = local_app_data / "Pulsar_Assistant"
        
        for i, task in enumerate(tasks):
            self.lbl_progress.config(text=task)
            self.progress['value'] = (i / len(tasks)) * 100
            self.update_idletasks()
            
            if task == "Extracting files...":
                self.extract_app()
            elif task == "Creating Desktop Shortcuts...":
                self.create_shortcut()
            else:
                time.sleep(1) # Fake delay to show progress for other steps
            
        self.progress['value'] = 100
        self.lbl_progress.config(text="Done!")
        
        # Save settings in the NEW installation directory
        self.settings_path = self.install_dir / "config" / "user_settings.json"
        self.save_settings()
        
        time.sleep(0.5)
        self.after(0, lambda: self.show_step(4))

    def extract_app(self):
        import shutil
        if not self.install_dir.exists():
            self.install_dir.mkdir(parents=True)
            
        # Copy main app directory (onedir build)
        bundled_dir = self.base_path / "Pulsar_Assistant"
        
        if bundled_dir.exists() and bundled_dir.is_dir():
            try:
                # Copy all contents from bundled_dir to install_dir
                shutil.copytree(bundled_dir, self.install_dir, dirs_exist_ok=True)
            except Exception as e:
                print(f"Extraction failed: {e}")
        else:
            print("Bundled directory not found, checking for executable fallback...")
            # Fallback to single exe
            bundled_exe = self.base_path / "Pulsar_Assistant.exe"
            dest_exe = self.install_dir / "Pulsar_Assistant.exe"
            if bundled_exe.exists():
                try:
                    shutil.copy2(bundled_exe, dest_exe)
                except Exception as e:
                    print(f"Extraction fallback failed: {e}")
            else:
                print("Bundled exe not found either, skipping copy for local testing.")
                time.sleep(1)
        
        # Copy uninstaller
        bundled_uninstaller = self.base_path / "Uninstall_Pulsar.exe"
        if bundled_uninstaller.exists():
            try:
                shutil.copy2(bundled_uninstaller, self.install_dir / "Uninstall_Pulsar.exe")
            except Exception as e:
                print(f"Uninstaller copy failed: {e}")
        
        # Copy icon
        bundled_icon = self.base_path / "icon.ico"
        if bundled_icon.exists():
            try:
                shutil.copy2(bundled_icon, self.install_dir / "icon.ico")
            except Exception as e:
                print(f"Icon copy failed: {e}")

    def create_shortcut(self):
        import tempfile
        desktop = Path(os.path.expanduser("~/Desktop"))
        shortcut_path = desktop / "Pulsar Assistant.lnk"
        target_path = self.install_dir / "Pulsar_Assistant.exe"
        icon_path = self.install_dir / "icon.ico"
        
        if target_path.exists():
            # Use VBScript to create shortcut with icon
            icon_line = f'oLink.IconLocation = "{icon_path}"' if icon_path.exists() else ''
            vbs_script = f"""
            Set oWS = WScript.CreateObject("WScript.Shell")
            sLinkFile = "{shortcut_path}"
            Set oLink = oWS.CreateShortcut(sLinkFile)
            oLink.TargetPath = "{target_path}"
            oLink.WorkingDirectory = "{self.install_dir}"
            {icon_line}
            oLink.Save
            """
            
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.vbs') as vbs:
                vbs.write(vbs_script)
                vbs_path = vbs.name
                
            try:
                subprocess.run(['cscript.exe', '//Nologo', vbs_path], creationflags=subprocess.CREATE_NO_WINDOW)
            finally:
                os.remove(vbs_path)
        else:
            time.sleep(1)
        
        # Register in Windows Add/Remove Programs
        self.register_uninstaller()

    def register_uninstaller(self):
        """Register app in Windows Add/Remove Programs"""
        try:
            import winreg
            uninstall_exe = self.install_dir / "Uninstall_Pulsar.exe"
            icon_path = self.install_dir / "icon.ico"
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PulsarAssistant"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Pulsar AI Assistant")
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, str(uninstall_exe))
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.install_dir))
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Pulsar")
                if icon_path.exists():
                    winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(icon_path))
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        except Exception as e:
            print(f"Registry registration failed (non-critical): {e}")

    def save_settings(self):
        try:
            if not self.settings_path.parent.exists():
                self.settings_path.parent.mkdir(parents=True)
                
            settings = {"onboarded": True, "theme": self.theme_var.get(), "mic_granted": self.mic_var.get()}
            
            if self.settings_path.exists():
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        data.update(settings)
                        settings = data
                    except:
                        pass
                        
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def finish_setup(self):
        if self.launch_var.get():
            target_path = getattr(self, 'install_dir', self.base_path) / "Pulsar_Assistant.exe"
            if target_path.exists():
                subprocess.Popen([str(target_path)], cwd=str(target_path.parent))
            else:
                # Fallback for dev environment
                app_script = self.base_path / "src" / "ai_assistant" / "apps" / "pulsar_app.py"
                if app_script.exists():
                    subprocess.Popen([sys.executable, str(app_script)])
        self.destroy()

if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
