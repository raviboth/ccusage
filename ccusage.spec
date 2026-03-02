# -*- mode: python ; coding: utf-8 -*-
import sys

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'plyer.platforms.macosx.notification',
        'plyer.platforms.linux.notification',
        'pyqtgraph',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Claude Code Usage Monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Claude Code Usage Monitor',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Claude Code Usage Monitor.app',
        icon=None,
        bundle_identifier='com.ccusage',
        info_plist={
            'LSUIElement': True,
            'CFBundleShortVersionString': '0.1.0',
            'NSHighResolutionCapable': True,
        },
    )
