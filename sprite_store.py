"""One resident static size; thumbnails never load a full-size sprite bank."""
from pathlib import Path
from PySide6.QtGui import QPixmap, QImage

EXTRA_ACTIONS = ('heart_finger','heart_chest','heart_overhead','drink')

NAMES = ['正面','侧面','背面','wave','heart','shy','happy','read','sit','sleep','eat','walk1','walk2','stretch','lift']

def read_pixmap(path):
    # QImage avoids Qt's implicit file-pixmap cache retaining released banks.
    image = QImage(str(path))
    if image.isNull():
        raise RuntimeError(f'预处理素材缺失，请运行 prepare_assets.py：{path}')
    return QPixmap.fromImage(image)


class SpriteStore(dict):
    def __init__(self, directory, height):
        super().__init__()
        self.directory = Path(directory) / 'prepared'
        self.height = None
        self.thumbs = {}
        self.ensure(height)

    def ensure(self, height):
        if height == self.height and self:
            return
        frames = {(name,height):read_pixmap(self.directory / str(height) / f'{name}.png') for name in NAMES}
        self.clear()
        self.update(frames)
        self.height = height

    def __missing__(self, key):
        name, height = key
        if name not in EXTRA_ACTIONS:
            raise KeyError(key)
        # Extra poses are not added to the resident static bank.
        return read_pixmap(self.directory / str(height) / f'{name}.png')

    def thumbnail(self, name):
        if name not in self.thumbs:
            self.thumbs[name] = read_pixmap(self.directory / 'thumbs' / f'{name}.png')
        return self.thumbs[name]

    def release(self):
        self.clear()
        self.height = None
