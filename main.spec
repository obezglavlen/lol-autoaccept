# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


tkinterdnd2_datas, tkinterdnd2_binaries, tkinterdnd2_hiddenimports = collect_all(
    'tkinterdnd2'
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=tkinterdnd2_binaries,
    datas=tkinterdnd2_datas,
    hiddenimports=tkinterdnd2_hiddenimports,
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
    name='lolautoaccept',
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
