# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['manak_desktop_app.py'],
    pathex=[],
    binaries=[
        ('chromedriver.exe', '.'),
    ],
    datas=[
        ('config', 'config'),
        ('job_cards_processor.py', '.'),
        ('multiple_jobs_processor.py', '.'),
        ('huid_data_processor.py', '.'),
        ('weight_capture_processor.py', '.'),
        ('request_generator.py', '.'),
        ('device_license.py', '.'),
        ('submit_huid_data_api.php', '.'),
        ('device_license_api.php', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        # Core Python modules
        'os', 'sys', 'time', 'random', 'json', 'base64', 'datetime', 'traceback',
        'threading', 'sqlite3', 'urllib', 'urllib.parse', 'urllib.request',
        
        # Tkinter modules
        'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext', 'tkinter.messagebox', 
        'tkinter.simpledialog', 'tkinter.filedialog', 'tkinter.colorchooser',
        
        # Selenium modules
        'selenium', 'selenium.webdriver', 'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service', 'selenium.webdriver.chrome.options',
        'selenium.webdriver.common.by', 'selenium.webdriver.common.keys',
        'selenium.webdriver.common.action_chains', 'selenium.webdriver.support',
        'selenium.webdriver.support.ui', 'selenium.webdriver.support.expected_conditions',
        'selenium.webdriver.support.wait', 'selenium.common.exceptions',
        'selenium.webdriver.remote', 'selenium.webdriver.remote.webdriver',
        'selenium.webdriver.remote.webelement', 'selenium.webdriver.remote.command',
        
        # MySQL connector modules
        'mysql', 'mysql.connector', 'mysql.connector.errors', 'mysql.connector.constants',
        'mysql.connector.connection', 'mysql.connector.cursor', 'mysql.connector.pooling',
        'mysql.connector.locales', 'mysql.connector.conversion', 'mysql.connector.utils',
        
        # Requests modules
        'requests', 'requests.adapters', 'requests.auth', 'requests.cookies',
        'requests.exceptions', 'requests.models', 'requests.sessions',
        'requests.utils', 'urllib3', 'urllib3.util', 'urllib3.exceptions',
        
        # Custom modules
        'job_cards_processor', 'multiple_jobs_processor', 'huid_data_processor',
        'weight_capture_processor', 'request_generator', 'device_license', 'config',
        
        # Additional dependencies that might be missing
        'encodings', 'encodings.utf_8', 'encodings.cp1252', 'encodings.latin_1',
        'collections', 'collections.abc', 'itertools', 'functools', 'operator',
        'copy', 'pickle', 'hashlib', 'hmac', 'ssl', 'socket', 'http', 'http.client',
        'email', 'email.mime', 'email.mime.text', 'email.mime.multipart',
        'xml', 'xml.etree', 'xml.etree.ElementTree', 'xml.parsers', 'xml.parsers.expat',
        're', 'math', 'statistics', 'decimal', 'fractions', 'calendar', 'locale',
        'platform', 'subprocess', 'shutil', 'glob', 'fnmatch', 'tempfile',
        'pathlib', 'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma', 'csv', 'configparser',
        'logging', 'logging.handlers', 'warnings', 'contextlib', 'weakref',
        'gc', 'inspect', 'ast', 'types', 'typing', 'dataclasses', 'enum',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'Pillow',  # Exclude heavy packages
        'jupyter', 'notebook', 'IPython',  # Exclude Jupyter
        'test', 'tests', 'testing',  # Exclude test modules
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,  # Disable optimization for better compatibility
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MANAK_Automations_v10_04',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX for Windows 7 compatibility
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for normal Windows app (no command window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version='version_info.txt',  # Version info for Windows properties
)
