"""
Pulsar AI Assistant - Production Windows 11 App Builder
=======================================================
Builds and registers the native Windows 11 desktop application:
1. Generates multi-resolution glowing icon: `assets/pulsar_app.ico` (16..256 px)
2. Compiles native windowless Win64 executable: `Pulsar.exe`
   - Zero console flash (`/target:winexe`)
   - Embedded Per-Monitor V2 DPI manifest
   - Embedded Windows Product/Version metadata (Pulsar AI Assistant v4.2.0)
   - Embedded multi-res `pulsar_app.ico`
   - Calls `SetCurrentProcessExplicitAppUserModelID("Pulsar.AIAssistant.App.v1")`
     + `AllowSetForegroundWindow(ASFW_ANY)` for instant foreground wakeup on 2nd click
3. Registers Start Menu shortcut (`%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Pulsar AI Assistant.lnk`)
   with Windows Shell `IPropertyStore` `System.AppUserModel.ID` stamped so Windows 11
   merges the pinned Taskbar icon and running Dashboard into ONE single native app icon.

Run:
    python scripts/build_windows_app.py
"""

import os
import sys
import math
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pulsar.host.windows_integration import PULSAR_APP_ID, PULSAR_DISPLAY_NAME

ASSETS_DIR = REPO_ROOT / "assets"
ICO_PATH = ASSETS_DIR / "pulsar_app.ico"
EXE_PATH = REPO_ROOT / "Pulsar.exe"


def generate_app_ico(out_ico: Path) -> Path:
    """Renders a crisp, flagship-quality multi-resolution Windows .ico (16..256 px)."""
    from PIL import Image, ImageDraw, ImageFilter

    out_ico.parent.mkdir(parents=True, exist_ok=True)

    # Render master at 512x512 for ultra-clean supersampled downscaling
    S = 512
    cx, cy = S / 2.0, S / 2.0
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 1. Deep cosmic rounded-circle badge background
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d_bg = ImageDraw.Draw(bg)
    pad = 22
    d_bg.ellipse([pad, pad, S - pad, S - pad], fill=(10, 15, 34, 255))
    img = Image.alpha_composite(img, bg)

    # 2. Multi-layer luminous cobalt -> cyan -> neon magenta radial glow
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d_glow = ImageDraw.Draw(glow)
    # Left cobalt-cyan bloom
    d_glow.ellipse([70, 85, 340, 395], fill=(0, 210, 255, 165))
    # Right indigo-magenta bloom
    d_glow.ellipse([175, 95, 440, 410], fill=(192, 38, 211, 165))
    # Center electric core
    d_glow.ellipse([155, 155, 357, 357], fill=(99, 102, 241, 210))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=42))

    # Clip glow inside circular badge
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([pad, pad, S - pad, S - pad], fill=255)
    glow_clipped = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    glow_clipped.paste(glow, (0, 0), mask)
    img = Image.alpha_composite(img, glow_clipped)

    # 3. Signature Pulsar 4D Wireframe Sphere lines + pinpoint starlight dots
    wire = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d_w = ImageDraw.Draw(wire)
    rad = 158.0

    # Latitude rings
    for lat_i in range(1, 8):
        phi = (lat_i / 8.0) * math.pi
        ring_r = math.sin(phi) * rad
        ring_y = cy - math.cos(phi) * rad * 0.92
        ring_h = max(4.0, ring_r * 0.28)
        t = lat_i / 8.0
        col = (
            int(0 * (1 - t) + 216 * t),
            int(230 * (1 - t) + 75 * t),
            int(255 * (1 - t) + 240 * t),
            185,
        )
        d_w.ellipse(
            [cx - ring_r, ring_y - ring_h, cx + ring_r, ring_y + ring_h],
            outline=col,
            width=3,
        )

    # Longitude meridians
    for lon_i in range(6):
        ang = (lon_i / 6.0) * math.pi
        rx = max(14.0, abs(math.cos(ang)) * rad)
        t = lon_i / 5.0
        col = (
            int(56 * (1 - t) + 192 * t),
            int(189 * (1 - t) + 56 * t),
            int(248 * (1 - t) + 235 * t),
            165,
        )
        d_w.ellipse(
            [cx - rx, cy - rad * 0.92, cx + rx, cy + rad * 0.92],
            outline=col,
            width=3,
        )

    # Pinpoint starlight particles on Fibonacci sphere
    n_pts = 72
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n_pts):
        y_n = 1.0 - (i / float(n_pts - 1)) * 2.0
        r_n = math.sqrt(max(0.0, 1.0 - y_n * y_n))
        th = golden * i
        px = cx + math.cos(th) * r_n * (rad * 1.06)
        py = cy + y_n * (rad * 0.98)
        t = (px - (cx - rad)) / (2.0 * rad)
        t = max(0.0, min(1.0, t))
        col = (
            int(0 * (1 - t) + 236 * t),
            int(243 * (1 - t) + 92 * t),
            int(255 * (1 - t) + 247 * t),
            245,
        )
        pr = 4.5 if (i % 3 == 0) else 3.0
        d_w.ellipse([px - pr, py - pr, px + pr, py + pr], fill=col)

    # Bright luminous core highlight
    d_w.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(224, 249, 255, 220))
    img = Image.alpha_composite(img, wire)

    # 4. Crisp outer neon border ring
    border = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(border).ellipse(
        [pad, pad, S - pad, S - pad],
        outline=(56, 189, 248, 225),
        width=8,
    )
    img = Image.alpha_composite(img, border)

    # Save multi-resolution Windows ICO
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(str(out_ico), format="ICO", sizes=ico_sizes)
    print(f"[BUILD] Generated multi-res icon: {out_ico} ({out_ico.stat().st_size:,} bytes)")
    return out_ico


CSHARP_LAUNCHER_SRC = r"""
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

[assembly: System.Reflection.AssemblyTitle("Pulsar AI Assistant")]
[assembly: System.Reflection.AssemblyDescription("Pulsar AI Assistant — Native Windows 11 Desktop Application")]
[assembly: System.Reflection.AssemblyCompany("Pulsar AI")]
[assembly: System.Reflection.AssemblyProduct("Pulsar AI Assistant")]
[assembly: System.Reflection.AssemblyVersion("4.2.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("4.2.0.0")]

namespace PulsarLauncher
{
    static class Program
    {
        private const string APP_ID = "__APP_ID__";
        private const uint ASFW_ANY = 0xFFFFFFFF;

        [DllImport("shell32.dll", SetLastError = true)]
        private static extern int SetCurrentProcessExplicitAppUserModelID(
            [MarshalAs(UnmanagedType.LPWStr)] string AppID);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool AllowSetForegroundWindow(uint dwProcessId);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

        [STAThread]
        static int Main(string[] args)
        {
            try
            {
                SetCurrentProcessExplicitAppUserModelID(APP_ID);
                // Grant foreground focus permission so 2nd taskbar click restores running Dashboard immediately
                AllowSetForegroundWindow(ASFW_ANY);

                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string pythonw = Path.Combine(baseDir, "venv", "Scripts", "pythonw.exe");
                string webPy = Path.Combine(baseDir, "web.py");

                if (!File.Exists(pythonw))
                {
                    pythonw = "pythonw.exe";
                }

                if (!File.Exists(webPy))
                {
                    MessageBoxW(
                        IntPtr.Zero,
                        "Could not find web.py in:\n" + baseDir + "\n\nKeep Pulsar.exe inside the Pulsar project folder.",
                        "Pulsar AI Assistant",
                        0x10);
                    return 1;
                }

                var argBuilder = new StringBuilder();
                argBuilder.Append("\"").Append(webPy).Append("\"");

                bool hasModeArg = false;
                foreach (string a in args)
                {
                    string low = a.ToLowerInvariant();
                    if (low == "--open" || low == "--tray" || low == "--minimized" || low == "--test-orb" || low == "--core-only")
                    {
                        hasModeArg = true;
                    }
                    argBuilder.Append(" ");
                    if (a.Contains(" "))
                        argBuilder.Append("\"").Append(a).Append("\"");
                    else
                        argBuilder.Append(a);
                }

                // Default when clicking Pulsar.exe / Taskbar icon: open the native Dashboard window
                if (!hasModeArg)
                {
                    argBuilder.Append(" --open");
                }

                var psi = new ProcessStartInfo
                {
                    FileName = pythonw,
                    Arguments = argBuilder.ToString(),
                    WorkingDirectory = baseDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                psi.EnvironmentVariables["PULSAR_LAUNCHED_BY_EXE"] = "1";

                Process.Start(psi);
                return 0;
            }
            catch (Exception ex)
            {
                MessageBoxW(
                    IntPtr.Zero,
                    "Failed to start Pulsar AI Assistant:\n\n" + ex.Message,
                    "Pulsar AI Assistant — Launch Error",
                    0x10);
                return 1;
            }
        }
    }
}
"""

APP_MANIFEST_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="4.2.0.0" processorArchitecture="amd64" name="Pulsar.AIAssistant" type="win32"/>
  <description>Pulsar AI Assistant Native Windows Desktop Application</description>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    </windowsSettings>
  </application>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
</assembly>
"""


def compile_native_exe(ico_path: Path, out_exe: Path) -> Path:
    """Compiles Pulsar.exe natively using Windows' built-in 64-bit C# compiler."""
    csc_candidates = [
        Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    ]
    csc = next((p for p in csc_candidates if p.exists()), None)
    if not csc:
        raise FileNotFoundError("Microsoft .NET csc.exe not found on this machine.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cs_file = tmp / "PulsarLauncher.cs"
        manifest_file = tmp / "Pulsar.exe.manifest"

        cs_file.write_text(CSHARP_LAUNCHER_SRC.replace("__APP_ID__", PULSAR_APP_ID), encoding="utf-8")
        manifest_file.write_text(APP_MANIFEST_XML, encoding="utf-8")

        cmd = [
            str(csc),
            "/nologo",
            "/target:winexe",
            "/platform:x64",
            "/optimize+",
            f"/win32icon:{ico_path}",
            f"/win32manifest:{manifest_file}",
            f"/out:{out_exe}",
            str(cs_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"csc.exe failed (code {res.returncode}):\n{res.stdout}\n{res.stderr}")

    print(f"[BUILD] Compiled native Windows executable: {out_exe} ({out_exe.stat().st_size:,} bytes)")
    return out_exe


def create_stamped_shortcut(lnk_path: Path, target_exe: Path, ico_path: Path, arguments: str = "") -> Path:
    """
    Creates a Windows .lnk shortcut and stamps System.AppUserModel.ID onto it via
    IPropertyStore so Windows 11 merges the pinned Taskbar icon with the live app!
    """
    import pythoncom
    from win32com.shell import shell
    from win32com.propsys import propsys, pscon

    lnk_path.parent.mkdir(parents=True, exist_ok=True)
    pythoncom.CoInitialize()
    try:
        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )
        shortcut.SetPath(str(target_exe))
        shortcut.SetWorkingDirectory(str(REPO_ROOT))
        if arguments:
            shortcut.SetArguments(arguments)
        shortcut.SetDescription("Pulsar AI Assistant — Decoupled Native Desktop AI")
        shortcut.SetIconLocation(str(ico_path), 0)

        # Stamp System.AppUserModel.ID directly onto the shortcut property store!
        prop_store = shortcut.QueryInterface(propsys.IID_IPropertyStore)
        prop_store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(PULSAR_APP_ID))
        prop_store.Commit()

        persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Save(str(lnk_path), 0)
        print(f"[BUILD] Registered Start Menu / App Shortcut: {lnk_path} (AppUserModelID={PULSAR_APP_ID})")
        return lnk_path
    finally:
        pythoncom.CoUninitialize()


def main():
    print("=" * 76)
    print("  PULSAR AI ASSISTANT — PRODUCTION WINDOWS 11 APP BUILDER")
    print("=" * 76)

    ico = generate_app_ico(ICO_PATH)
    exe = compile_native_exe(ico, EXE_PATH)

    # Register in Windows Start Menu Programs so searching "Pulsar" in Start finds it
    start_menu_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu_lnk = start_menu_dir / f"{PULSAR_DISPLAY_NAME}.lnk"
    create_stamped_shortcut(start_menu_lnk, exe, ico)

    # Also place a convenient pinned-ready shortcut right in the project root
    repo_lnk = REPO_ROOT / f"{PULSAR_DISPLAY_NAME}.lnk"
    create_stamped_shortcut(repo_lnk, exe, ico)

    print("\n" + "=" * 76)
    print("  BUILD COMPLETE!")
    print(f"  * Native App EXE:     {exe}")
    print(f"  * Multi-Res App Icon: {ico}")
    print(f"  * Start Menu Entry:   {start_menu_lnk}")
    print(f"  * AppUserModelID:     {PULSAR_APP_ID}")
    print("=" * 76)


if __name__ == "__main__":
    main()
