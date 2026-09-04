# -*- mode: python ; coding: utf-8 -*-
import os
from kivy_deps import sdl2, glew
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree

project_dir = os.path.abspath(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        ('database.py', '.'),
        ('pdf_generator.py', '.'),
    ],
    hiddenimports=[
        'sqlite3',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        'reportlab.platypus',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.colors',
        'reportlab.lib.styles',
        'PIL',
        'PIL.Image',
        'kivy',
        'kivy.core.window',
        'kivy.core.text',
        'kivy.core.image',
        'kivy.graphics',
        'kivy.graphics.cgl_backend',
        'kivy.graphics.cgl_backend.cgl_glew',
        'kivy.graphics.cgl_backend.cgl_sdl2',
        'pandas',
        'openpyxl',
        'openpyxl.reader.excel',
        'tkinter',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CashBook',
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
    Tree(project_dir, excludes=['dist', 'build', '.git', '.github', 'bin', '.buildozer', '__pycache__']),
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CashBook',
)
