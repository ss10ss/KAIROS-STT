# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for KairosSTT — build with: pyinstaller KairosSTT.spec"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

hiddenimports = [
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "tokenizers",
    "av",
    "sounddevice",
    "keyboard",
    "pystray",
    "pyautogui",
    "pyperclip",
    "PIL",
    "numpy",
    "pkg_resources.py2_warn",
]

datas = []
binaries = []

for package in ("faster_whisper", "ctranslate2", "onnxruntime", "av", "tokenizers"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["kairos_stt.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="KairosSTT",
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
)
