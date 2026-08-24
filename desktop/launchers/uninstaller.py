import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
from pathlib import Path
import sys

class UninstallWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pulsar Assistant - Uninstall")
        self.geometry("450x300")
        self.resizable(False, False)
        
        # Determine install directory
        local_app_data = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
        self.install_dir = local_app_data / "Pulsar_Assistant"
        self.desktop_shortcut = Path(os.path.expanduser("~/Desktop")) / "Pulsar Assistant.lnk"
        
        # Configure style
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Red.Horizontal.TProgressbar', background='#dc3545')
        self.configure(bg='#f0f0f0')
        
        # Main content
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        ttk.Label(self.main_frame, text="Uninstall Pulsar Assistant", style='Header.TLabel').pack(pady=(10, 20))
        
        ttk.Label(
            self.main_frame,
            text="This will completely remove Pulsar Assistant from your computer,\n"
                 "including the application files and Desktop shortcut.\n\n"
                 "Your personal data in the Knowledge Graph will also be deleted.",
            justify="center", wraplength=400
        ).pack(pady=10)
        
        self.progress = ttk.Progressbar(
            self.main_frame, style='Red.Horizontal.TProgressbar',
            orient="horizontal", length=350, mode="determinate"
        )
        
        self.status_label = ttk.Label(self.main_frame, text="")
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=15)
        ttk.Separator(self, orient='horizontal').pack(side="bottom", fill="x", pady=5)
        
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=5)
        
        self.btn_uninstall = ttk.Button(btn_frame, text="Uninstall", command=self.start_uninstall)
        self.btn_uninstall.pack(side="right", padx=5)
    
    def start_uninstall(self):
        confirm = messagebox.askyesno(
            "Confirm Uninstall",
            "Are you sure you want to completely remove Pulsar Assistant?\n\n"
            "This action cannot be undone."
        )
        if not confirm:
            return
        
        self.btn_uninstall.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        self.progress.pack(pady=10)
        self.status_label.pack(pady=5)
        
        import threading
        threading.Thread(target=self.run_uninstall, daemon=True).start()
    
    def run_uninstall(self):
        import time
        
        steps = [
            ("Removing Desktop shortcut...", self.remove_shortcut),
            ("Removing application files...", self.remove_app_files),
            ("Cleaning up registry...", self.cleanup_registry),
            ("Finalizing...", lambda: time.sleep(0.5)),
        ]
        
        for i, (label, action) in enumerate(steps):
            self.status_label.config(text=label)
            self.progress['value'] = (i / len(steps)) * 100
            self.update_idletasks()
            try:
                action()
            except Exception as e:
                print(f"Uninstall step failed: {e}")
            time.sleep(0.5)
        
        self.progress['value'] = 100
        self.status_label.config(text="Uninstallation complete.")
        self.update_idletasks()
        
        messagebox.showinfo(
            "Uninstall Complete",
            "Pulsar Assistant has been successfully removed from your computer."
        )
        self.destroy()
    
    def remove_shortcut(self):
        if self.desktop_shortcut.exists():
            self.desktop_shortcut.unlink()
    
    def remove_app_files(self):
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)
    
    def cleanup_registry(self):
        """Remove Add/Remove Programs entry"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PulsarAssistant"
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass  # Key doesn't exist, nothing to clean
        except Exception as e:
            print(f"Registry cleanup failed: {e}")


if __name__ == "__main__":
    app = UninstallWizard()
    app.mainloop()
