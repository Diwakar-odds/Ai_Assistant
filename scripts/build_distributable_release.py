"""
Pulsar AI Assistant - Full Offline Distributable Windows Release Builder
========================================================================
Creates a 100% standalone, shareable Windows 10/11 release inside `dist_release/`:

  dist_release/
  ├── PulsarSetup.exe             (Native Windows 11 GUI Installer Wizard)
  └── Pulsar_AI_Assistant/        (Portable Standalone App — double-click Pulsar.exe!)
      ├── Pulsar.exe              (PyInstaller Dual-Mode Paradigm B Native App)
      ├── UninstallPulsar.exe     (Native Windows Uninstaller)
      ├── _internal/              (Self-contained Python + PySide6 + QtWebEngine + AI/Audio DLLs + React UI)
      ├── models/                 (100% Offline Models: GGUF 4.7GB + Whisper-Hinglish 924MB + KittenTTS 78MB)
      ├── .env.example            (Clean template — ZERO personal API keys!)
      └── README_FIRST.txt        (Simple guide for sharing with friends)

Usage:
    python scripts/build_distributable_release.py
    python scripts/build_distributable_release.py --skip-pyinstaller  (re-run installer/models step only)
"""

import os
import sys
import shutil
import argparse
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_ROOT = REPO_ROOT / "dist_release"
APP_BUNDLE_DIR = DIST_ROOT / "Pulsar_AI_Assistant"
BUILD_WORK_DIR = REPO_ROOT / "build_release_tmp"
ICO_PATH = REPO_ROOT / "assets" / "pulsar_app.ico"
SPEC_PATH = REPO_ROOT / "pulsar_release.spec"

APP_ID = "Pulsar.AIAssistant.App.v1"

# ---------------------------------------------------------------------------
# Native C# Windows 11 Setup Wizard (PulsarSetup.exe)
# ---------------------------------------------------------------------------
INSTALLER_CS = r"""
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("Pulsar AI Assistant Setup")]
[assembly: System.Reflection.AssemblyDescription("Installer for Pulsar AI Assistant (Full Offline Edition)")]
[assembly: System.Reflection.AssemblyCompany("Pulsar AI")]
[assembly: System.Reflection.AssemblyProduct("Pulsar AI Assistant")]
[assembly: System.Reflection.AssemblyVersion("4.2.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("4.2.0.0")]

namespace PulsarSetup
{
    static class ShellShortcutHelper
    {
        [StructLayout(LayoutKind.Sequential, Pack = 4)]
        private struct PROPERTYKEY
        {
            public Guid fmtid;
            public uint pid;
        }

        [StructLayout(LayoutKind.Explicit)]
        private struct PROPVARIANT
        {
            [FieldOffset(0)] public ushort vt;
            [FieldOffset(8)] public IntPtr ptr;
        }

        [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
        private class CShellLink { }

        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
        private interface IShellLinkW
        {
            void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszFile, int cchMaxPath, IntPtr pfd, uint fFlags);
            void GetIDList(out IntPtr ppidl);
            void SetIDList(IntPtr pidl);
            void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszName, int cchMaxName);
            void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);
            void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszDir, int cchMaxPath);
            void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);
            void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszArgs, int cchMaxPath);
            void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);
            void GetHotkey(out ushort pwHotkey);
            void SetHotkey(ushort wHotkey);
            void GetShowCmd(out int piShowCmd);
            void SetShowCmd(int iShowCmd);
            void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszIconPath, int cchIconPath, out int piIcon);
            void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);
            void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, uint dwReserved);
            void Resolve(IntPtr hwnd, uint fFlags);
            void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
        }

        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
        private interface IPropertyStore
        {
            void GetCount(out uint cProps);
            void GetAt(uint iProp, out PROPERTYKEY pkey);
            void GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
            void SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
            void Commit();
        }

        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("0000010b-0000-0000-C000-000000000046")]
        private interface IPersistFile
        {
            void GetClassID(out Guid pClassID);
            void IsDirty();
            void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, uint dwMode);
            void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, [MarshalAs(UnmanagedType.Bool)] bool fRemember);
            void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
            void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
        }

        public static void CreateShortcut(string lnkPath, string targetExe, string workDir, string iconPath, string description, string appUserModelId)
        {
            var link = (IShellLinkW)new CShellLink();
            link.SetPath(targetExe);
            link.SetWorkingDirectory(workDir);
            link.SetDescription(description);
            if (File.Exists(iconPath))
                link.SetIconLocation(iconPath, 0);

            var propStore = (IPropertyStore)link;
            var key = new PROPERTYKEY
            {
                fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
                pid = 5 // PKEY_AppUserModel_ID
            };
            IntPtr strPtr = Marshal.StringToCoTaskMemUni(appUserModelId);
            try
            {
                var pv = new PROPVARIANT { vt = 31 /* VT_LPWSTR */, ptr = strPtr };
                propStore.SetValue(ref key, ref pv);
                propStore.Commit();
            }
            finally
            {
                Marshal.FreeCoTaskMem(strPtr);
            }

            var pf = (IPersistFile)link;
            Directory.CreateDirectory(Path.GetDirectoryName(lnkPath));
            pf.Save(lnkPath, true);
        }
    }

    public class SetupForm : Form
    {
        private const string APP_NAME = "Pulsar AI Assistant";
        private const string APP_ID = "Pulsar.AIAssistant.App.v1";
        private const string APP_VER = "4.2.0";

        private TextBox txtInstallDir;
        private CheckBox chkDesktop;
        private CheckBox chkStartMenu;
        private CheckBox chkAutostart;
        private CheckBox chkLaunchAfter;
        private ProgressBar progressBar;
        private Label lblStatus;
        private Label lblDetail;
        private Button btnInstall;
        private Button btnBrowse;
        private Button btnClose;

        private string sourceDir;
        private bool isInstalling = false;
        private bool installDone = false;

        public SetupForm()
        {
            sourceDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Pulsar_AI_Assistant");
            string defaultDest = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                "Pulsar AI Assistant");

            this.Text = "Pulsar AI Assistant — Setup Wizard";
            this.ClientSize = new Size(560, 415);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(15, 23, 42);
            this.ForeColor = Color.FromArgb(241, 245, 249);
            this.Font = new Font("Segoe UI", 9.5f);

            var lblTitle = new Label
            {
                Text = "Pulsar AI Assistant v4.2 (Full Offline Edition)",
                Font = new Font("Segoe UI", 15f, FontStyle.Bold),
                ForeColor = Color.FromArgb(56, 189, 248),
                Location = new Point(24, 20),
                Size = new Size(512, 32)
            };
            this.Controls.Add(lblTitle);

            var lblSub = new Label
            {
                Text = "Zero Python required. Includes 4D Wireframe Orb, Voice Wake ('Hey Pulsar'),\nOffline Hinglish Whisper STT, KittenTTS, and Local 8B GGUF AI Engine.",
                ForeColor = Color.FromArgb(148, 163, 184),
                Location = new Point(24, 56),
                Size = new Size(512, 38)
            };
            this.Controls.Add(lblSub);

            var lblDir = new Label
            {
                Text = "Installation Folder:",
                Location = new Point(24, 108),
                Size = new Size(200, 20)
            };
            this.Controls.Add(lblDir);

            txtInstallDir = new TextBox
            {
                Text = defaultDest,
                Location = new Point(24, 130),
                Size = new Size(420, 26),
                BackColor = Color.FromArgb(30, 41, 59),
                ForeColor = Color.White,
                BorderStyle = BorderStyle.FixedSingle
            };
            this.Controls.Add(txtInstallDir);

            btnBrowse = new Button
            {
                Text = "Browse...",
                Location = new Point(452, 129),
                Size = new Size(84, 27),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(51, 65, 85),
                ForeColor = Color.White
            };
            btnBrowse.FlatAppearance.BorderColor = Color.FromArgb(71, 85, 105);
            btnBrowse.Click += (s, e) =>
            {
                using (var dlg = new FolderBrowserDialog { SelectedPath = txtInstallDir.Text })
                {
                    if (dlg.ShowDialog() == DialogResult.OK)
                        txtInstallDir.Text = Path.Combine(dlg.SelectedPath, "Pulsar AI Assistant");
                }
            };
            this.Controls.Add(btnBrowse);

            chkDesktop = new CheckBox
            {
                Text = "Create Desktop Shortcut (Pulsar AI Assistant)",
                Checked = true,
                Location = new Point(24, 172),
                Size = new Size(380, 24)
            };
            this.Controls.Add(chkDesktop);

            chkStartMenu = new CheckBox
            {
                Text = "Add to Windows Start Menu (Taskbar Pin-Ready)",
                Checked = true,
                Location = new Point(24, 198),
                Size = new Size(380, 24)
            };
            this.Controls.Add(chkStartMenu);

            chkAutostart = new CheckBox
            {
                Text = "Start Pulsar automatically in System Tray when Windows starts",
                Checked = false,
                Location = new Point(24, 224),
                Size = new Size(460, 24)
            };
            this.Controls.Add(chkAutostart);

            chkLaunchAfter = new CheckBox
            {
                Text = "Launch Pulsar AI Assistant right after installation",
                Checked = true,
                Location = new Point(24, 250),
                Size = new Size(420, 24)
            };
            this.Controls.Add(chkLaunchAfter);

            progressBar = new ProgressBar
            {
                Location = new Point(24, 290),
                Size = new Size(512, 22),
                Style = ProgressBarStyle.Continuous
            };
            this.Controls.Add(progressBar);

            lblStatus = new Label
            {
                Text = "Ready to install. No Administrator permissions required.",
                ForeColor = Color.FromArgb(226, 232, 240),
                Location = new Point(24, 318),
                Size = new Size(512, 20)
            };
            this.Controls.Add(lblStatus);

            lblDetail = new Label
            {
                Text = "",
                ForeColor = Color.FromArgb(148, 163, 184),
                Location = new Point(24, 338),
                Size = new Size(512, 18)
            };
            this.Controls.Add(lblDetail);

            btnInstall = new Button
            {
                Text = "Install Pulsar",
                Location = new Point(316, 368),
                Size = new Size(130, 34),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(37, 99, 235),
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 10f, FontStyle.Bold)
            };
            btnInstall.FlatAppearance.BorderSize = 0;
            btnInstall.Click += OnInstallClick;
            this.Controls.Add(btnInstall);

            btnClose = new Button
            {
                Text = "Cancel",
                Location = new Point(456, 368),
                Size = new Size(80, 34),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(51, 65, 85),
                ForeColor = Color.White
            };
            btnClose.FlatAppearance.BorderSize = 0;
            btnClose.Click += (s, e) => { if (!isInstalling) this.Close(); };
            this.Controls.Add(btnClose);
        }

        private async void OnInstallClick(object sender, EventArgs e)
        {
            if (installDone)
            {
                if (chkLaunchAfter.Checked)
                {
                    string exe = Path.Combine(txtInstallDir.Text.Trim(), "Pulsar.exe");
                    if (File.Exists(exe))
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = exe,
                            WorkingDirectory = txtInstallDir.Text.Trim(),
                            UseShellExecute = true
                        });
                    }
                }
                this.Close();
                return;
            }

            if (!Directory.Exists(sourceDir) || !File.Exists(Path.Combine(sourceDir, "Pulsar.exe")))
            {
                MessageBox.Show(
                    "Could not find the 'Pulsar_AI_Assistant' application folder next to PulsarSetup.exe!\n\n" +
                    "Make sure you copied the full release folder containing both PulsarSetup.exe and Pulsar_AI_Assistant\\.",
                    APP_NAME + " Setup",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }

            string destDir = txtInstallDir.Text.Trim();
            if (string.IsNullOrEmpty(destDir)) return;

            isInstalling = true;
            btnInstall.Enabled = false;
            btnBrowse.Enabled = false;
            btnClose.Enabled = false;
            txtInstallDir.Enabled = false;

            try
            {
                lblStatus.Text = "Scanning application files and offline AI models...";
                var files = await Task.Run(() => Directory.GetFiles(sourceDir, "*", SearchOption.AllDirectories));
                long totalBytes = 0;
                foreach (var f in files) totalBytes += new FileInfo(f).Length;
                if (totalBytes <= 0) totalBytes = 1;

                long copiedBytes = 0;
                Directory.CreateDirectory(destDir);

                await Task.Run(() =>
                {
                    byte[] buffer = new byte[1024 * 1024]; // 1 MB fast streaming buffer
                    foreach (var srcFile in files)
                    {
                        string rel = srcFile.Substring(sourceDir.Length).TrimStart('\\', '/');
                        string dstFile = Path.Combine(destDir, rel);
                        Directory.CreateDirectory(Path.GetDirectoryName(dstFile));

                        this.BeginInvoke((Action)(() =>
                        {
                            lblDetail.Text = rel;
                        }));

                        using (var inFs = new FileStream(srcFile, FileMode.Open, FileAccess.Read, FileShare.Read))
                        using (var outFs = new FileStream(dstFile, FileMode.Create, FileAccess.Write, FileShare.None))
                        {
                            int read;
                            while ((read = inFs.Read(buffer, 0, buffer.Length)) > 0)
                            {
                                outFs.Write(buffer, 0, read);
                                copiedBytes += read;
                                int pct = (int)Math.Min(100, (copiedBytes * 100L) / totalBytes);
                                double mbDone = copiedBytes / (1024.0 * 1024.0);
                                double mbTotal = totalBytes / (1024.0 * 1024.0);
                                this.BeginInvoke((Action)(() =>
                                {
                                    progressBar.Value = pct;
                                    lblStatus.Text = string.Format("Installing Pulsar AI Assistant... {0}% ({1:F0} / {2:F0} MB)", pct, mbDone, mbTotal);
                                }));
                            }
                        }
                    }
                });

                lblStatus.Text = "Creating Windows 11 shortcuts and registering application...";
                string installedExe = Path.Combine(destDir, "Pulsar.exe");
                string installedIco = Path.Combine(destDir, "_internal", "assets", "pulsar_app.ico");
                if (!File.Exists(installedIco)) installedIco = installedExe;

                if (chkStartMenu.Checked)
                {
                    string sm = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                        "Programs",
                        APP_NAME + ".lnk");
                    ShellShortcutHelper.CreateShortcut(sm, installedExe, destDir, installedIco, APP_NAME, APP_ID);
                }

                if (chkDesktop.Checked)
                {
                    string desk = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                        APP_NAME + ".lnk");
                    ShellShortcutHelper.CreateShortcut(desk, installedExe, destDir, installedIco, APP_NAME, APP_ID);
                }

                if (chkAutostart.Checked)
                {
                    using (var rk = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true))
                    {
                        if (rk != null) rk.SetValue("PulsarAIAssistant", "\"" + installedExe + "\" --tray");
                    }
                }

                // Register in Windows Settings -> Installed Apps (Add/Remove Programs)
                string uninstExe = Path.Combine(destDir, "UninstallPulsar.exe");
                using (var uk = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\PulsarAIAssistant"))
                {
                    uk.SetValue("DisplayName", APP_NAME);
                    uk.SetValue("DisplayVersion", APP_VER);
                    uk.SetValue("Publisher", "Pulsar AI");
                    uk.SetValue("InstallLocation", destDir);
                    uk.SetValue("DisplayIcon", installedIco);
                    uk.SetValue("UninstallString", "\"" + uninstExe + "\"");
                    uk.SetValue("NoModify", 1, RegistryValueKind.DWord);
                    uk.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                    uk.SetValue("EstimatedSize", (int)(totalBytes / 1024L), RegistryValueKind.DWord);
                }

                progressBar.Value = 100;
                lblStatus.Text = "Installation Complete! Pin Pulsar to your Taskbar anytime.";
                lblDetail.Text = "Installed to: " + destDir;
                installDone = true;
                btnInstall.Text = "Finish";
                btnInstall.Enabled = true;
                btnClose.Text = "Close";
                btnClose.Enabled = true;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Installation failed:\n\n" + ex.Message, APP_NAME + " Setup", MessageBoxButtons.OK, MessageBoxIcon.Error);
                btnInstall.Enabled = true;
                btnClose.Enabled = true;
            }
            finally
            {
                isInstalling = false;
            }
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm());
        }
    }
}
"""

# ---------------------------------------------------------------------------
# Native C# Uninstaller (UninstallPulsar.exe)
# ---------------------------------------------------------------------------
UNINSTALLER_CS = r"""
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("Uninstall Pulsar AI Assistant")]
[assembly: System.Reflection.AssemblyProduct("Pulsar AI Assistant")]
[assembly: System.Reflection.AssemblyVersion("4.2.0.0")]

namespace PulsarUninstaller
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            var res = MessageBox.Show(
                "Are you sure you want to uninstall Pulsar AI Assistant?\n\n" +
                "This will remove the application files, Start Menu & Desktop shortcuts, and auto-start entry.",
                "Uninstall Pulsar AI Assistant",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question);

            if (res != DialogResult.Yes) return;

            try
            {
                string appDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');

                // Remove Start Menu & Desktop shortcuts
                string sm = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu), "Programs", "Pulsar AI Assistant.lnk");
                string desk = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Pulsar AI Assistant.lnk");
                if (File.Exists(sm)) File.Delete(sm);
                if (File.Exists(desk)) File.Delete(desk);

                // Remove Autostart & Uninstall registry keys
                using (var rk = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true))
                {
                    if (rk != null) rk.DeleteValue("PulsarAIAssistant", false);
                }
                Registry.CurrentUser.DeleteSubKeyTree(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\PulsarAIAssistant", false);

                // Schedule self-deletion of install directory after uninstaller exits
                string cmd = string.Format("/C timeout /t 2 /nobreak >nul & rmdir /s /q \"{0}\"", appDir);
                Process.Start(new ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = cmd,
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    WindowStyle = ProcessWindowStyle.Hidden
                });

                MessageBox.Show(
                    "Pulsar AI Assistant has been uninstalled successfully.",
                    "Uninstall Complete",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Uninstall error:\n" + ex.Message, "Uninstall Pulsar AI Assistant", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
"""


def _find_csc() -> Path:
    for p in (
        Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    ):
        if p.exists():
            return p
    raise FileNotFoundError("Windows .NET csc.exe compiler not found.")


def compile_cs_winexe(source_code: str, out_exe: Path, ico_path: Path, extra_refs=None):
    csc = _find_csc()
    refs = ["System.dll", "System.Drawing.dll", "System.Windows.Forms.dll"]
    if extra_refs:
        refs.extend(extra_refs)

    with tempfile.TemporaryDirectory() as tmp:
        cs_file = Path(tmp) / (out_exe.stem + ".cs")
        cs_file.write_text(source_code, encoding="utf-8")
        cmd = [
            str(csc),
            "/nologo",
            "/target:winexe",
            "/platform:x64",
            "/optimize+",
            f"/win32icon:{ico_path}",
            f"/out:{out_exe}",
        ] + [f"/r:{r}" for r in refs] + [str(cs_file)]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed compiling {out_exe.name}:\n{res.stdout}\n{res.stderr}")
    print(f"[RELEASE] Compiled {out_exe} ({out_exe.stat().st_size:,} bytes)")


def run_pyinstaller_build():
    pyinstaller = REPO_ROOT / "venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller.exists():
        raise FileNotFoundError(f"PyInstaller not found at {pyinstaller}")

    DIST_ROOT.mkdir(parents=True, exist_ok=True)

    # Preserve already-copied 5.6 GB offline models across fast rebuilds (instant rename on same drive)
    models_live = APP_BUNDLE_DIR / "models"
    models_cache = DIST_ROOT / "_models_preserve_tmp"
    moved_models = False
    if models_live.exists() and not models_cache.exists():
        print("[RELEASE] Preserving existing 5.6 GB models/ folder during PyInstaller rebuild...")
        shutil.move(str(models_live), str(models_cache))
        moved_models = True

    cmd = [
        str(pyinstaller),
        "--noconfirm",
        "--clean",
        "--distpath", str(DIST_ROOT),
        "--workpath", str(BUILD_WORK_DIR),
        str(SPEC_PATH),
    ]
    print(f"[RELEASE] Running PyInstaller: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, cwd=str(REPO_ROOT))
        if res.returncode != 0:
            raise RuntimeError(f"PyInstaller failed with exit code {res.returncode}")
    finally:
        if moved_models and models_cache.exists():
            APP_BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
            if models_live.exists():
                shutil.rmtree(models_live, ignore_errors=True)
            shutil.move(str(models_cache), str(models_live))
            print("[RELEASE] Restored preserved models/ folder instantaneously.")

    print(f"[RELEASE] PyInstaller standalone app built at: {APP_BUNDLE_DIR}")


def copy_clean_offline_models():
    """Copies ONLY the 3 clean runtime offline models (NO personal data or training backups)."""
    src_models = REPO_ROOT / "models"
    dst_models = APP_BUNDLE_DIR / "models"
    dst_models.mkdir(parents=True, exist_ok=True)

    # 1. Local Offline GGUF LLM (4.69 GB)
    gguf_src = src_models / "pulsar-final-q4_k_m.gguf"
    gguf_dst = dst_models / "pulsar-final-q4_k_m.gguf"
    if gguf_src.exists():
        if not gguf_dst.exists() or gguf_dst.stat().st_size != gguf_src.stat().st_size:
            print(f"[RELEASE] Copying offline LLM ({gguf_src.stat().st_size / (1024**3):.2f} GB)...")
            shutil.copy2(gguf_src, gguf_dst)
        else:
            print("[RELEASE] Offline LLM already up-to-date in bundle.")
    else:
        print("[WARN] models/pulsar-final-q4_k_m.gguf not found!")

    # 2. Offline Hinglish Whisper STT (924 MB) + KittenTTS (78 MB)
    for folder_name in ("whisper-hinglish", "tts"):
        s_dir = src_models / folder_name
        d_dir = dst_models / folder_name
        if s_dir.exists():
            src_count = sum(1 for f in s_dir.rglob("*") if f.is_file())
            dst_count = sum(1 for f in d_dir.rglob("*") if f.is_file()) if d_dir.exists() else -1
            if dst_count == src_count:
                print(f"[RELEASE] models/{folder_name} already up-to-date ({dst_count} files).")
            else:
                print(f"[RELEASE] Copying models/{folder_name}...")
                shutil.copytree(s_dir, d_dir, dirs_exist_ok=True)
        else:
            print(f"[WARN] models/{folder_name} not found!")


def write_clean_templates():
    """Writes clean non-secret .env.example & friend README into the distributable bundle."""
    env_example = REPO_ROOT / "config" / ".env.example"
    if env_example.exists():
        shutil.copy2(env_example, APP_BUNDLE_DIR / ".env.example")

    readme = APP_BUNDLE_DIR / "README_FIRST.txt"
    readme.write_text(
        "=====================================================================\n"
        "  PULSAR AI ASSISTANT v4.2 — FULL OFFLINE WINDOWS 11 EDITION\n"
        "=====================================================================\n\n"
        "NO PYTHON INSTALLATION OR API KEY REQUIRED!\n\n"
        "HOW TO USE:\n"
        "  Option A (Install as a real Windows App — Recommended):\n"
        "    1. Double-click 'PulsarSetup.exe' (outside this folder).\n"
        "    2. Follow the wizard (no Admin rights needed).\n"
        "    3. Pin 'Pulsar AI Assistant' from Start Menu to your Taskbar!\n\n"
        "  Option B (Portable Mode — No Install):\n"
        "    1. Open this 'Pulsar_AI_Assistant' folder.\n"
        "    2. Double-click 'Pulsar.exe' directly!\n\n"
        "FEATURES INCLUDED 100% OFFLINE:\n"
        "  * Native Dashboard + 136px Transparent 4D Wireframe Glowing Orb\n"
        "  * System Tray Icon (check '^' next to clock; drag out to pin)\n"
        "  * Local 8B GGUF AI Engine (models\\pulsar-final-q4_k_m.gguf)\n"
        "  * Offline Hinglish Speech Recognition (models\\whisper-hinglish)\n"
        "  * Offline Neural Voice TTS (models\\tts)\n"
        "  * Close [X] hides to Tray & reveals the 4D Orb; right-click Tray -> 'Quit Pulsar' to exit.\n\n"
        "OPTIONAL CLOUD AI:\n"
        "  To also enable Google Gemini Cloud AI, open Settings inside Pulsar\n"
        "  or rename '.env.example' to '.env' and add your GEMINI_API_KEY.\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Build Distributable Pulsar Windows 11 Release")
    parser.add_argument("--skip-pyinstaller", action="store_true", help="Skip PyInstaller compile if bundle already exists")
    args = parser.parse_args()

    if not ICO_PATH.exists():
        raise FileNotFoundError(f"Icon missing: {ICO_PATH}. Run scripts/build_windows_app.py first.")

    if not args.skip_pyinstaller:
        run_pyinstaller_build()

    if not (APP_BUNDLE_DIR / "Pulsar.exe").exists():
        raise RuntimeError(f"Expected frozen Pulsar.exe not found at {APP_BUNDLE_DIR / 'Pulsar.exe'}")

    # Compile Uninstaller inside bundle + Setup Wizard beside bundle
    compile_cs_winexe(UNINSTALLER_CS, APP_BUNDLE_DIR / "UninstallPulsar.exe", ICO_PATH)
    compile_cs_winexe(INSTALLER_CS, DIST_ROOT / "PulsarSetup.exe", ICO_PATH)

    copy_clean_offline_models()
    write_clean_templates()

    # Final privacy verification: ensure ZERO personal files leaked into dist_release
    for forbidden in (".env", "contacts.json", "encryption.key", "user_settings.json"):
        leaks = [p for p in DIST_ROOT.rglob(forbidden)]
        assert not leaks, f"PRIVACY LEAK DETECTED: {leaks}"

    total_gb = sum(f.stat().st_size for f in DIST_ROOT.rglob("*") if f.is_file()) / (1024 ** 3)
    print("\n" + "=" * 78)
    print("  PULSAR AI ASSISTANT — DISTRIBUTABLE WINDOWS RELEASE READY!")
    print(f"  * Release Folder to Share: {DIST_ROOT}")
    print(f"  * Windows Installer:       {DIST_ROOT / 'PulsarSetup.exe'}")
    print(f"  * Portable Standalone App: {APP_BUNDLE_DIR / 'Pulsar.exe'}")
    print(f"  * Total Offline Size:      {total_gb:.2f} GB (0 personal keys/data leaked!)")
    print("=" * 78)


if __name__ == "__main__":
    main()
