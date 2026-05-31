
# Hook for pywebview
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('webview')

hiddenimports += [
    'webview',
    'webview.window',
    'webview.guilib',
    'clr',
]
