# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pdf_merger.py'],
    pathex=[],
    binaries=[],
    datas=[('/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/customtkinter', 'customtkinter'), ('/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/tkinterdnd2', 'tkinterdnd2')],
    hiddenimports=['fitz', 'PIL', 'PIL.Image', 'customtkinter', 'darkdetect', 'tkinterdnd2'],
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
    [],
    exclude_binaries=True,
    name='PDF Merger',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDF Merger',
)
app = BUNDLE(
    coll,
    name='PDF Merger.app',
    icon=None,
    bundle_identifier=None,
)
