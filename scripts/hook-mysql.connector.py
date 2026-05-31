
# Hook for mysql-connector-python
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('mysql.connector')

hiddenimports += [
    'mysql.connector.locales.eng',
    'mysql.connector.plugins.caching_sha2_password',
    'mysql.connector.plugins.mysql_native_password',
]
