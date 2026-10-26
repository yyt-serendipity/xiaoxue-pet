# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
prepared = root/'sprites-anime'/'prepared'
datas = []
# Ship only the selectable sprite sizes and thumbnails, never source art or private JSON.
for folder in ('119', '187', '238', 'thumbs'):
    for file in (prepared/folder).rglob('*'):
        if not file.is_file() or file.suffix not in ('.png', '.json'):
            continue
        if file.parent.name == 'rig' or 'rig' in file.parts:
            continue
        datas.append((str(file), str(Path('sprites-anime/prepared')/file.relative_to(prepared).parent)))
datas += [(str(prepared/'manifest.json'), 'sprites-anime/prepared'),
          (str(root/'LICENSE'), '.'), (str(root/'THIRD_PARTY_NOTICES.md'), '.'),
          (str(root/'packaging/third-party-licenses'), 'third-party-licenses')]
a = Analysis([str(root/'main.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['pynvml', 'numpy', 'cv2', 'PySide6.QtQml', 'PySide6.QtQuick',
                       'PySide6.QtOpenGL', 'PySide6.QtSql', 'PySide6.QtTest'],
             noarchive=False, optimize=1)
# Qt 6.12 uses Windows' system ICU API. Do not shadow it with unrelated PATH
# copies (e.g. Poppler/Conda ICU exports version-suffixed, incompatible symbols).
a.binaries = [item for item in a.binaries if not Path(item[0]).name.lower().startswith('icu')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='XiaoxuePet',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          icon=[str(root/'companion-avatar.ico')])
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='XiaoxuePet')
