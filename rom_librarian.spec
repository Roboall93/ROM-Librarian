# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['rom_manager.py'],
    pathex=[],
    binaries=[
        ('chdman.exe', '.'),  # Include chdman utility for CHD conversion
    ],
    datas=[
        ('cartridge.ico', '.'),  # Include the icon file
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'ttkbootstrap',
        'ttkbootstrap.localization',
        'ttkbootstrap.themes',
        'PIL',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        # py7zr and its dependencies (dynamic imports not auto-detected by PyInstaller)
        'py7zr',
        'py7zr.py7zr',
        'py7zr.helpers',
        'py7zr.callbacks',
        'py7zr.compressor',
        'py7zr.properties',
        'texttable',
        'Cryptodome',
        'Cryptodome.Cipher',
        'Cryptodome.Cipher.AES',
        'brotli',
        'psutil',
        'pyppmd',
        'pybcj',
        'multivolumefile',
        'inflate64',
        'backports',
        'backports.zstd',
    ],
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
    [],
    exclude_binaries=True,  # Don't bundle everything into one file
    name='ROM Librarian',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='cartridge.ico',  # Set the app icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ROM Librarian',
)
