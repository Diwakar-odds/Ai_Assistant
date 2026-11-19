# -*- mode: python ; coding: utf-8 -*-
"""
Pulsar AI Assistant - Production PyInstaller Release Specification
==================================================================
Builds a standalone, zero-Python-required Windows 11 `--onedir` application:
    dist_release/Pulsar_AI_Assistant/Pulsar.exe

Security & Privacy Guarantees:
- ZERO personal `.env`, `contacts.json`, `encryption.key`, `data/` DBs, or `logs/`.
- ZERO training backups (`models/backup_old`, `offline_command_model`, `finetuned_v4_lora`).
- 100% Paradigm B dual-mode binary (`Pulsar.exe` Host + `Pulsar.exe --core-subprocess` Core).
"""

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve()

datas = [
    (str(ROOT / "frontend" / "web-app" / "dist"), "frontend/web-app/dist"),
    (str(ROOT / "assets" / "pulsar_app.ico"), "assets"),
    (str(ROOT / "pulsar" / "core" / "static"), "pulsar/core/static"),
    (str(ROOT / "backend" / "templates"), "backend/templates"),
    (str(ROOT / "config" / ".env.example"), "config"),
    (str(ROOT / "config" / "user_settings.json.example"), "config"),
    (str(ROOT / "config" / "voice_config.json"), "config"),
    (str(ROOT / "config" / "multimodal_config.json.example"), "config"),
]

binaries = []
hiddenimports = [
    # Pulsar Paradigm B packages
    "pulsar",
    "pulsar.logging_setup",
    "pulsar.host",
    "pulsar.host.__main__",
    "pulsar.host.console_ui",
    "pulsar.host.core_supervisor",
    "pulsar.host.dashboard_window",
    "pulsar.host.job_object",
    "pulsar.host.orb_window",
    "pulsar.host.tray_app",
    "pulsar.host.windows_integration",
    "pulsar.core",
    "pulsar.core.__main__",
    "pulsar.core.server",
    "pulsar.core.orb_state",
    "pulsar.core.routes_health",
    "pulsar.core.watchdog",
    "pulsar.audio",
    "pulsar.audio.mic_stream",
    "pulsar.audio.worker",
    # Flask / Socket.IO / EngineIO threading transports
    "engineio.async_drivers.threading",
    "socketio",
    "flask_socketio",
    "flask_cors",
    "flask_jwt_extended",
    "werkzeug",
    "simple_websocket",
    "wsproto",
    # Windows COM / Shell / Taskbar identity
    "pythoncom",
    "pywintypes",
    "win32com.shell",
    "win32com.propsys.propsys",
    "win32com.propsys.pscon",
    "win32gui",
    "win32api",
    "win32con",
    "win32process",
    # Core runtime deps
    "sounddevice",
    "edge_tts",
    "mss",
    "psutil",
    "PIL",
    "requests",
    "dotenv",
]

# Include all internal project submodules dynamically
for pkg in ("backend", "core_ai"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# Collect native binaries & package metadata for AI / Audio engines
for pkg_bin in ("llama_cpp", "_sounddevice_data", "_soundfile_data", "ctranslate2", "onnxruntime", "espeakng_loader"):
    try:
        binaries += collect_dynamic_libs(pkg_bin)
        datas += collect_data_files(pkg_bin)
    except Exception:
        pass

for pkg_all in (
    "kittentts",
    "misaki",
    "phonemizer",
    "language_tags",
    "segments",
    "csvw",
    "clldutils",
    "faster_whisper",
    "chromadb",
    "tokenizers",
):
    try:
        d, b, h = collect_all(pkg_all)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# Also collect clean metadata/data files for NLP, timezone, SSL & voice packages
for pkg_data in ("transformers", "sentence_transformers", "certifi", "tzdata", "pytz", "speech_recognition"):
    try:
        datas += collect_data_files(pkg_data, include_py_files=False)
    except Exception:
        pass

excludes = [
    "pytest",
    "_pytest",
    "tkinter",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    "tensorboard",
    "peft",
    "trl",
    "datasets",
    "bitsandbytes",
    "sphinx",
    "setuptools.tests",
]

a = Analysis(
    [str(ROOT / "pulsar" / "frozen_entry.py")],
    pathex=[str(ROOT), str(ROOT / "backend"), str(ROOT / "core_ai")],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pulsar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "pulsar_app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Pulsar_AI_Assistant",
)
