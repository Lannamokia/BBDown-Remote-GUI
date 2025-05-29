from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 包含所有必要的PyQt5子模块
hiddenimports = collect_submodules('PyQt5')

# 包含所有必要的PyQt5数据文件
datas = collect_data_files('PyQt5', include_py_files=True)

# 排除不必要的模块以减小体积
excludedimports = [
    'PyQt5.QtWebEngine',
    'PyQt5.QtWebEngineCore',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtWebSockets',
    'PyQt5.QtBluetooth',
    'PyQt5.QtNfc',
    'PyQt5.QtSql',
    'PyQt5.QtTest'
]

# 过滤掉不必要的模块
hiddenimports = [m for m in hiddenimports if not any(m.startswith(ex) for ex in excludedimports]