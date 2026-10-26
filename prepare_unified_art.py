"""Offline full-figure atlas compiler. Never imported by the running pet.

Only crops/resizes complete generated figures; no limb layers or body rig.
The original wave/blink/walk art remains the character style reference.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / '.asset-build-tools'))
import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

HEIGHTS = (119, 187, 238, 306, 64)
HEARTS = ('heart_finger', 'heart_chest', 'heart_overhead')


def figures(path, columns, rows):
    """Locate whole figures instead of cutting through uneven generated gutters."""
    source = QImage(str(path))
    rgba = cv2.imdecode(np.frombuffer(Path(path).read_bytes(), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if source.isNull() or rgba is None or rgba.shape[2] != 4:
        raise RuntimeError(f'Missing transparent source: {path}')
    _, _, stats, _ = cv2.connectedComponentsWithStats((rgba[:, :, 3] > 127).astype(np.uint8))
    boxes = [tuple(map(int, b[:4])) for b in stats[1:] if b[4] > 10000]
    if len(boxes) != columns * rows:
        raise RuntimeError(f'{path}: expected {columns * rows} complete figures, found {len(boxes)}')
    ordered = []
    for row in range(rows):
        selected = [b for b in boxes if int((b[1] + b[3] / 2) * rows / source.height()) == row]
        if len(selected) != columns:
            raise RuntimeError(f'{path}: bad row {row}')
        ordered += sorted(selected, key=lambda b: b[0])
    return [source.copy(x, y, w, h) for x, y, w, h in ordered]


def fit(figure, height, relative=.93, crown_offset=0, anchor_feet=False):
    """Translate/scale the entire drawing, preserving all proportions and alpha."""
    scale = height * relative / (figure.height() - crown_offset)
    # Wide sleeping/lifted poses must also fit the lightweight runtime canvas.
    scale = min(scale, height * 1.01 / figure.width())
    anchor = figure.width() / 2
    if anchor_feet:
        pixels = figure.convertToFormat(QImage.Format.Format_RGBA8888)
        arr = np.frombuffer(pixels.bits(), np.uint8).reshape(pixels.height(), pixels.width(), 4)
        ys, xs = np.where(arr[round(figure.height() * .87):, :, 3] > 127)
        if xs.size:
            anchor = (int(xs.min()) + int(xs.max())) / 2
    canvas = QImage(round(height * 1.05), height, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRectF(canvas.width()/2-anchor*scale, height*.97-figure.height()*scale,
                            figure.width()*scale, figure.height()*scale), figure)
    painter.end()
    return canvas


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(path)):
        raise RuntimeError(f'Cannot save {path}')


def prepare_unified(directory):
    directory = Path(directory)
    source = directory / 'unified-source'
    prepared = directory / 'prepared'
    metadata = {'version': 1, 'style_reference': 'unified-source/style-reference.png',
                'runtime_heights': [119, 187, 238], 'full_figure_only': True, 'sources': {}}
    for name in ('care', 'expressions', 'drink', 'heart-finger', 'heart-chest', 'heart-overhead'):
        path = source / f'{name}.png'
        metadata['sources'][name] = hashlib.sha256(path.read_bytes()).hexdigest()

    care = figures(source/'care.png', 2, 2)
    expressions = figures(source/'expressions.png', 2, 2)
    drink = figures(source/'drink.png', 2, 2)
    hearts = {name: figures(source/(name.replace('_', '-')+'.png'), 3, 2) for name in HEARTS}
    for height in HEIGHTS:
        out = prepared / ('thumbs' if height == 64 else str(height))
        for name, figure in zip(('read', 'sit', 'sleep', 'eat'), care):
            save(fit(figure, height, .48 if name == 'sleep' else .80), out/f'{name}.png')
        for name, figure in zip(('shy', 'happy', 'stretch', 'lift'), expressions):
            save(fit(figure, height, crown_offset=29 if name == 'stretch' else 0), out/f'{name}.png')
        for i, figure in enumerate(drink):
            frame = fit(figure, height, anchor_feet=True)
            if height != 64:
                save(frame, out/'drink'/f'{i}.png')
            if i == 2:
                save(frame, out/'drink.png')
        for name, images in hearts.items():
            for i, figure in enumerate(images):
                # The hands rise above the cap. Keep crown-to-feet height stable.
                offset = 25 if name == 'heart_overhead' and i >= 4 else 0
                frame = fit(figure, height, crown_offset=offset, anchor_feet=True)
                if height != 64:
                    save(frame, out/'heart-smooth'/name/f'{i}.png')
                    if i < 4:
                        # Older four-frame fallback assets share the same identity.
                        fallback = (1, 3, 4, 5)[i]
                        fallback_offset = 25 if name == 'heart_overhead' and fallback >= 4 else 0
                        save(fit(images[fallback], height, crown_offset=fallback_offset, anchor_feet=True),
                             out/name/f'{i}.png')
                if i == 4:
                    save(frame, out/f'{name}.png')
                    if name == 'heart_chest':
                        save(frame, out/'heart.png')
            if height != 64:
                # Eight-frame fallback retains a lowering pose and neutral ending.
                save(fit(images[2], height, anchor_feet=True), out/'heart-smooth'/name/'6.png')
                save(fit(images[0], height, anchor_feet=True), out/'heart-smooth'/name/'7.png')
        # Reuse the approved continuous artwork for the corresponding static poses.
        base = prepared / str(height if height != 64 else 306)
        for name, rel in (('正面','blink-cycle/0.png'), ('wave','wave-cycle/2.png'),
                          ('walk1','walk-cycle/0.png'), ('walk2','walk-cycle/2.png')):
            frame = QImage(str(base/rel))
            if frame.isNull():
                raise RuntimeError(f'Missing approved base frame {base/rel}')
            if height == 64:
                frame = frame.scaled(round(height*1.05), height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
            save(frame, out/f'{name}.png')
    (prepared/'unified-art.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Unified full-figure artwork: 3 heart sequences, drink, 8 care/expression poses, matching thumbnails.', flush=True)


if __name__ == '__main__':
    app = QApplication([])
    prepare_unified(ROOT/'sprites-anime')
    from build_heart_motion import build
    build()
