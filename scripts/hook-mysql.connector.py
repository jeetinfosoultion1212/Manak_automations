# PyInstaller hook for mysql-connector-python
# This ensures all MySQL connector modules are properly included

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all mysql.connector submodules
hiddenimports = collect_submodules('mysql.connector')

# Ensure authentication plugins are included
hiddenimports += [
    'mysql.connector.plugins.mysql_native_password',
    'mysql.connector.plugins.caching_sha2_password',
    'mysql.connector.plugins.sha256_password',
]

# Collect all data files and binaries
datas, binaries, hiddenimports2 = collect_all('mysql.connector')

hiddenimports += hiddenimports2
