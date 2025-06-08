# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/ningxi/Desktop/bbd/BBDown-Remote-GUI/bbdown_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('bbdown_icon.ico', '.')],
    hiddenimports=[],
    hookspath=['hooks'],
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
    name='BBDown-GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=['bbdown_icon.ico'],
)
app = BUNDLE(
    exe,
    name='BBDown-GUI.app',
    icon='bbdown_icon.ico',
    bundle_identifier=None,
)
