# -*- mode: python ; coding: utf-8 -*-
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..', '..'))

datas = [
    (os.path.join(ROOT, 'dist_package', 'Pulsar_AI_Assistant'), 'Pulsar_AI_Assistant'),
    (os.path.join(ROOT, 'dist_package', 'Uninstall_Pulsar.exe'), '.'),
    (os.path.join(ROOT, 'assets', 'icon.ico'), '.'),
    (os.path.join(ROOT, 'docs', 'LICENSE.txt'), 'docs'),
]

a = Analysis(
    [os.path.join(ROOT, 'desktop', 'launchers', 'installer.py')],
    pathex=[ROOT, os.path.join(ROOT, 'desktop', 'launchers')],
    binaries=[],
    datas=datas,
    hiddenimports=['keyring', 'keyring.backends.Windows'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Setup_Pulsar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(ROOT, 'assets', 'icon.ico')],
)
