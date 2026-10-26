"""Check complete transparent character assets; no image generation or network calls."""
from pathlib import Path
import argparse
import json
import os
import struct
import sys

RAW = {'turnaround.png': (3, 1), 'walk-cycle.png': (4, 2),
       'wave-cycle.png': (3, 2), 'blink-cycle.png': (4, 1),
       'unified-source/heart-finger.png': (3, 2),
       'unified-source/heart-chest.png': (3, 2),
       'unified-source/heart-overhead.png': (3, 2),
       'unified-source/care.png': (2, 2), 'unified-source/expressions.png': (2, 2),
       'unified-source/drink.png': (2, 2), 'unified-source/style-reference.png': (1, 1)}
POSES = ('正面', '侧面', '背面', 'read', 'sit', 'sleep', 'eat', 'shy', 'happy',
         'stretch', 'lift', 'drink', 'heart_finger', 'heart_chest', 'heart_overhead',
         'heart', 'wave', 'walk1', 'walk2')
SEQUENCES = {'walk-cycle': 8, 'wave-cycle': 6, 'blink-cycle': 4, 'drink': 4,
             **{'heart-motion/'+a: 41 for a in ('heart_finger', 'heart_chest', 'heart_overhead')},
             **{'action-motion/'+a: n for a, n in (('walk', 72), ('wave', 54), ('drink', 27))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--stage', choices=('raw', 'prepared'), required=True)
    parser.add_argument('--make-icon', action='store_true')
    args = parser.parse_args()
    if args.make_icon and args.stage != 'prepared':
        parser.error('--make-icon requires --stage prepared')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage
    from PySide6.QtCore import QBuffer, QIODevice, Qt
    app = QApplication([])
    root = args.project.resolve()
    sys.path.insert(0, str(root))
    from animation import alpha_bounds
    checks, errors = 0, []

    def check(path, expected=None):
        nonlocal checks
        image = QImage(str(path))
        if image.isNull():
            raise ValueError('missing or unreadable PNG')
        if not image.hasAlphaChannel():
            raise ValueError('no alpha channel')
        bounds = alpha_bounds(image)
        if bounds.isEmpty():
            raise ValueError('empty character')
        corners = ((0, 0), (image.width()-1, 0), (0, image.height()-1), (image.width()-1, image.height()-1))
        if any(image.pixelColor(x, y).alpha() > 8 for x, y in corners):
            raise ValueError('opaque corner: check background and cropping')
        if expected and (image.width(), image.height()) != expected:
            raise ValueError(f'wrong size: expected {expected}')
        checks += 1
        return image

    if args.stage == 'raw':
        for name, (cols, rows) in RAW.items():
            try:
                image = check(root/'sprites-anime'/name)
                for row in range(rows):
                    for col in range(cols):
                        cell = image.copy(round(col*image.width()/cols), round(row*image.height()/rows),
                                          image.width()//cols, image.height()//rows)
                        if alpha_bounds(cell).isEmpty():
                            raise ValueError(f'empty grid cell {row},{col}')
                if name.startswith('unified-source/') and not name.endswith('style-reference.png'):
                    from prepare_unified_art import figures
                    figures(root/'sprites-anime'/name, cols, rows)
            except (ValueError, RuntimeError) as error:
                errors.append(f'{name}: {error}')
    else:
        base = root/'sprites-anime/prepared'
        for height in (64, 119, 187, 238):
            folder = 'thumbs' if height == 64 else str(height)
            names = [p+'.png' for p in POSES]
            if height != 64:
                names += [f'{action}/{i}.png' for action, count in SEQUENCES.items() for i in range(count)]
            for name in names:
                try:
                    check(base/folder/name, (round(height*1.05), height))
                except ValueError as error:
                    errors.append(f'{folder}/{name}: {error}')
        for name in ('manifest.json', 'unified-art.json'):
            try:
                json.loads((base/name).read_text(encoding='utf-8'))
            except (OSError, ValueError) as error:
                errors.append(f'{name}: {error}')
        for height in (119, 187, 238):
            for action, count in (('walk', 72), ('wave', 54), ('drink', 27)):
                name = f'{height}/action-motion/{action}/manifest.json'
                try:
                    data = json.loads((base/name).read_text(encoding='utf-8'))
                    if data['version'] != 1 or data['count'] != count:
                        raise ValueError('unexpected motion bank version or frame count')
                    for start, steps in data['edges'].values():
                        if not (0 <= start < start + steps < count):
                            raise ValueError('edge outside bank')
                    if not all(0 <= i < count for i in data['keyframes'].values()):
                        raise ValueError('keyframe outside bank')
                except (OSError, ValueError, KeyError, TypeError) as error:
                    errors.append(f'{name}: {error}')
        if not errors and args.make_icon:
            picture = QImage(str(base/'238/正面.png')).scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            from PySide6.QtGui import QPainter
            icon = QImage(256, 256, QImage.Format.Format_ARGB32)
            icon.fill(Qt.GlobalColor.transparent)
            painter = QPainter(icon)
            painter.drawImage((256-picture.width())//2, (256-picture.height())//2, picture)
            painter.end()
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if not icon.save(buffer, 'PNG'):
                raise RuntimeError('Icon PNG encoding failed')
            data = bytes(buffer.data())
            (root/'companion-avatar.ico').write_bytes(struct.pack('<HHH', 0, 1, 1) + struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(data), 22) + data)
    report = {'stage': args.stage, 'checked_images': checks, 'errors': errors,
              'visual_identity_and_motion': 'requires visual review'}
    (root/('art-validation-'+args.stage+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
