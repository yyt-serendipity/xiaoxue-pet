"""Collect notices for distributed dependencies without bundling build dependencies."""
from pathlib import Path
import importlib.metadata as metadata
import shutil
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'packaging/third-party-licenses'
DEST.mkdir(parents=True, exist_ok=True)
packages = ('PySide6-Essentials', 'shiboken6', 'requests', 'certifi', 'charset-normalizer', 'idna', 'urllib3', 'psutil')
versions = []
for name in packages:
    dist = metadata.distribution(name)
    versions.append(f'{name}=={dist.version}')
    for entry in dist.files or []:
        if any(word in entry.name.upper() for word in ('LICENSE', 'COPYING', 'NOTICE')):
            # Commercial-license references aren't the selected LGPL distribution terms.
            if 'COMMERCIAL' in entry.name.upper():
                continue
            src = Path(dist.locate_file(entry))
            if src.is_file():
                folder = DEST/name
                folder.mkdir(exist_ok=True)
                shutil.copy2(src, folder/entry.name)
python_license = Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():
    shutil.copy2(python_license, DEST/'Python-LICENSE.txt')
bootloader = metadata.distribution('pyinstaller')
for entry in bootloader.files or []:
    if entry.name == 'COPYING.txt':
        shutil.copy2(bootloader.locate_file(entry), DEST/'PyInstaller-COPYING.txt')
for filename, url in (
    ('LGPL-3.0.txt', 'https://www.gnu.org/licenses/lgpl-3.0.txt'),
    ('GPL-3.0.txt', 'https://www.gnu.org/licenses/gpl-3.0.txt'),
    ('Qt-third-party-licenses.html', 'https://doc.qt.io/qt-6/licenses-used-in-qt.html'),
    ('PySide-third-party-licenses.html', 'https://doc.qt.io/qtforpython-6/licenses.html'),
):
    path = DEST/filename
    if not path.exists():
        with urlopen(url, timeout=40) as response:
            path.write_bytes(response.read())
(DEST/'VERSIONS.txt').write_text('\n'.join(versions)+'\n', encoding='utf-8')
print('Collected dependency licenses and exact runtime versions.')
