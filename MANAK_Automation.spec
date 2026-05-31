# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect dependencies
pywebview_datas = []
pywebview_binaries = []
pywebview_hiddenimports = []

try:
    tmp_ret = collect_all('webview')
    pywebview_datas += tmp_ret[0]
    pywebview_binaries += tmp_ret[1]
    pywebview_hiddenimports += tmp_ret[2]
except:
    pass

# All processor modules
processor_hiddenimports = [
    'src.processors.job_cards_processor',
    'src.processors.delivery_voucher_processor',
    'src.processors.weight_capture_processor',
    'src.processors.multiple_jobs_processor',
    'src.processors.bulk_jobs_report_submit',
    'src.processors.huid_data_processor',
    'src.processors.request_generator',
    'src.processors.embedded_browser_processor',
]

# All hidden imports
hiddenimports = [
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.chrome.options',
    'selenium.webdriver.chrome.service',
    'selenium.webdriver.common.by',
    'selenium.webdriver.common.keys',
    'selenium.webdriver.support',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'selenium.common.exceptions',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'requests',
    'mysql.connector',
    'mysql.connector.locales.eng',
    'mysql.connector.plugins.caching_sha2_password',
    'mysql.connector.plugins.mysql_native_password',
    'src.license.device_license',
    'src.license.license_methods',
    'webview',
    'webview.window',
] + processor_hiddenimports + pywebview_hiddenimports

a = Analysis(
    ['src/manak_desktop_app.py'],
    pathex=['.', 'src', 'src/processors', 'src/license'],
    binaries=[
        ('drivers/chromedriver.exe', 'drivers'),
    ] + pywebview_binaries,
    datas=[
        ('config', 'config'),
        ('src/license', 'src/license'),
        ('src/processors', 'src/processors'),
    ] + pywebview_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy'],
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
    name='MANAK_Automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
