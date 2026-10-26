"""Compile original atlases into small runtime PNGs; originals remain untouched."""
import hashlib
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter
from animation import load_frames_raw, alpha_bounds

def prepare(directory):
    directory = Path(directory)
    output = directory / 'prepared'
    output.mkdir(exist_ok=True)
    heights = [119, 187, 238, 306]
    raw = {}
    sheet = QPixmap(str(directory / 'turnaround.png'))
    for i, name in enumerate(['正面', '侧面', '背面']):
        raw[(name, 306)] = sheet.copy(i * sheet.width() // 3, 0, sheet.width() // 3, sheet.height())
    for (name, _), pix in raw.items():
        bounds = alpha_bounds(pix.toImage())
        image = pix.toImage()
        band = alpha_bounds(image.copy(0, bounds.y() + round(bounds.height() * .1),
                                      image.width(), max(1, round(bounds.height() * .1))))
        anchor = band.center().x()
        if name == 'sleep':
            anchor = bounds.center().x()
        relative = .73 if name in ('sit', 'read', 'eat') else .48 if name == 'sleep' else .93
        for height in heights + [64]:
            canvas = QPixmap(round(height * 1.05), height)
            canvas.fill(Qt.GlobalColor.transparent)
            scale = height * relative / bounds.height()
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(QRectF(canvas.width() / 2 + (bounds.x() - anchor) * scale,
                                      height * .97 - bounds.height() * scale,
                                      bounds.width() * scale, bounds.height() * scale), pix, QRectF(bounds))
            painter.end()
            dest = output / ('thumbs' if height == 64 else str(height))
            dest.mkdir(exist_ok=True)
            if not canvas.save(str(dest / f'{name}.png')):
                raise RuntimeError(f'Cannot save {name}')
    for stem, columns, rows in [('walk-cycle', 4, 2), ('wave-cycle', 3, 2), ('blink-cycle', 4, 1)]:
        bank = load_frames_raw(directory / f'{stem}.png', columns, rows, heights)
        for height, frames in bank.items():
            dest = output / str(height) / stem
            dest.mkdir(exist_ok=True)
            for i, frame in enumerate(frames):
                if not frame.save(str(dest / f'{i}.png')):
                    raise RuntimeError(f'Cannot save {stem}/{i}')
    from prepare_unified_art import prepare_unified
    prepare_unified(directory)
    from build_heart_motion import build
    build()
    from build_action_motion import build as build_actions
    build_actions()
    sources = ['turnaround.png','walk-cycle.png','wave-cycle.png','blink-cycle.png']
    (output / 'manifest.json').write_text(json.dumps({'version':1,'heights':heights,
        'sources':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in sources}},indent=2),encoding='utf-8')
    print(f'Prepared {len(list(output.rglob("*.png")))} PNG assets, originals retained')

if __name__ == '__main__':
    app = QApplication([])
    prepare(Path(__file__).parent / 'sprites-anime')
