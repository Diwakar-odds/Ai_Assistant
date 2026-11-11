# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, '..', '..'))

datas = [
    (os.path.join(ROOT, 'backend'), 'backend'),
    (os.path.join(ROOT, 'core_ai'), 'core_ai'),
    (os.path.join(ROOT, 'shared'), 'shared'),
    (os.path.join(ROOT, 'assets'), 'assets'),
    (os.path.join(ROOT, 'desktop'), 'desktop'),
    (os.path.join(ROOT, 'docs', 'LICENSE.txt'), 'docs'),
    (os.path.join(ROOT, 'frontend', 'web-app', 'dist'), os.path.join('frontend', 'web-app', 'dist')),
]

binaries = []
extra_hiddenimports = []

for _pkg in (
    'espeakng_loader',
    'misaki',
    'phonemizer',
    'kittentts',
    'spacy',
    'thinc',
    'av',
    'onnxruntime',
    'faster_whisper',
    'sounddevice',
    'indic_transliteration',
):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas.extend(_d)
        binaries.extend(_b)
        extra_hiddenimports.extend(_h)
    except Exception:
        pass

vosk_dir = os.path.join(ROOT, 'venv', 'Lib', 'site-packages', 'vosk')
if os.path.exists(vosk_dir):
    datas.append((vosk_dir, 'vosk'))

# Always bundle the compact offline KittenTTS mini-0.8 (~78 MB) neural voice model
kitten_mini_dir = os.path.join(ROOT, 'models', 'tts', 'kitten-tts-mini-0.8')
if os.path.isdir(kitten_mini_dir):
    datas.append((kitten_mini_dir, os.path.join('models', 'tts', 'kitten-tts-mini-0.8')))

# Multi-GB model checkpoints (backup_old / finetuned_v4_lora / large GGUFs) are excluded
# from the base installer bundle by default so Setup_Pulsar.exe stays under Windows PE limits.
# Set PULSAR_BUNDLE_MODELS=1 only if explicitly bundling a model folder alongside dist_package.
if os.environ.get('PULSAR_BUNDLE_MODELS') == '1':
    gguf_path = os.path.join(ROOT, 'models', 'pulsar-final-q4_k_m.gguf')
    if os.path.exists(gguf_path):
        datas.append((gguf_path, 'models'))

a = Analysis(
    [os.path.join(ROOT, 'desktop', 'app_launcher.py')],
    pathex=[
        ROOT,
        os.path.join(ROOT, 'backend'),
        os.path.join(ROOT, 'core_ai', 'src'),
        os.path.join(ROOT, 'shared'),
        os.path.join(ROOT, 'desktop'),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'flask',
        'flask_socketio',
        'flask_cors',
        'flask_jwt_extended',
        'flask_limiter',
        'engineio.async_drivers.threading',
        'socketio',
        'webview',
        'pystray',
        'PIL',
        'PIL.Image',
        'edge_tts',
        'kittentts',
        'kittentts.onnx_model',
        'espeakng_loader',
        'misaki',
        'misaki.en',
        'phonemizer',
        'num2words',
        'av',
        'onnxruntime',
        'indic_transliteration',
        'indic_transliteration.sanscript',
        'speech_recognition',
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'keyring',
        'keyring.backends.Windows',
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'win32com',
        'win32com.client',
        'win32clipboard',
        'win32file',
        'win32service',
        'pythoncom',
        'pywintypes',
        'psutil',
        'dotenv',
        'cryptography',
        'sqlite3',
        'pygame',
        'sounddevice',
        'soundfile',
        'noisereduce',
        'pyaudio',
        'pynput',
        'pywinauto',
        'pyautogui',
        'pygetwindow',
        'pycaw',
        'comtypes',
        'keyboard',
        'mss',
        'cv2',
        'numpy',
        'vosk',
        'faster_whisper',
        'google.genai',
        'google.generativeai',
        'openai',
        'requests',
        'aiohttp',
        'bs4',
        'yaml',
        'pydantic',
        'deep_translator',
        'diskcache',
        'apscheduler',
        'schedule',
        'chromadb',
        'selenium',
        'spotipy',
        'yt_dlp',
        'ytmusicapi',
        'static_ffmpeg',
        'screen_brightness_control',
        'settings_manager',
        'modern_web_backend',
        'companion_app',
        'companion_bridge',
        'companion_voice',
        'agent_brain',
        'voice_service',
        'telemetry_dashboard',
        'telemetry_tracer',
        'ai_assistant.voice.tts_output_service',
        'ai_assistant.voice.text_cleaner',
        'ai_assistant.voice.echo_guard',
        'ai_assistant.voice.voice_settings_manager',
        'ai_assistant.core.jarvis_persona',
        'ai_assistant.core.local_command_normalizer',
        'routes',
        'routes.auth_routes',
        'routes.chain_routes',
        'routes.chat_routes',
        'routes.common',
        'routes.file_routes',
        'routes.learning_routes',
        'routes.local_ai_routes',
        'routes.settings_routes',
        'routes.system_routes',
        'routes.taskbar_routes',
        'routes.web_routes',
    ] + list(dict.fromkeys(extra_hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['webrtcvad'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pulsar_AI_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(ROOT, 'assets', 'icon.ico')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pulsar_AI_Assistant',
)
