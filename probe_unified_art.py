"""Compare full-figure assets at identical runtime size/cache limits."""
from pathlib import Path
import json
import statistics
import sys
import time
import psutil
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontDatabase
from PySide6.QtCore import Qt
from animation import Animator, HEART_ACTIONS
from sprite_store import SpriteStore

app = QApplication([])
QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent/'sprites-anime'
now = [0.]
animator = Animator(root, [238], clock=lambda: now[0])
sprites = SpriteStore(root, 238)
times = []
pair_bytes = 0
for action in ('正面', 'wave', *HEART_ACTIONS, 'drink', 'read', 'sleep'):
    for i in range(180):
        now[0] += .02
        start = time.perf_counter()
        animator.render((action, 238, 1), sprites, 0)
        times.append((time.perf_counter()-start)*1000)
        if action in HEART_ACTIONS:
            bank = animator.frames[action][238]
            assert len(bank.resident) <= 2
            pair_bytes = max(pair_bytes, sum(p.width()*p.height()*4 for p in bank.resident.values()))
        assert animator.cache_bytes <= 2*1024*1024
memory = psutil.Process().memory_info()
assert 'cv2' not in sys.modules and 'numpy' not in sys.modules
print(json.dumps({'asset_root': str(root), 'working_set_mib': round(memory.rss/2**20, 2),
                  'private_mib': round(memory.private/2**20, 2), 'pair_mib': round(pair_bytes/2**20, 3),
                  'cache_limit_mib': animator.cache_budget/2**20,
                  'render_median_ms': round(statistics.median(times), 3),
                  'render_p95_ms': round(sorted(times)[int(len(times)*.95)], 3)}), flush=True)

if len(sys.argv) == 1:
    canvas = QImage(1200, 690, QImage.Format.Format_ARGB32)
    canvas.fill(QColor('#faf8f5'))
    painter = QPainter(canvas)
    painter.setFont(QFont('Microsoft YaHei UI', 10))
    for row, action in enumerate(HEART_ACTIONS):
        now[0] = 0
        player = Animator(root, [187], clock=lambda: now[0])
        player.timeline.rate = 1.5
        player.render((action, 187, 1), sprites, 0)
        for col, t in enumerate((0, .2, .42, .7, 1.12, 2.4)):
            now[0] = t
            frame = player.render((action, 187, 1), sprites, 0)
            painter.drawPixmap(col*200+2, row*230, frame)
            painter.setPen(QColor('#303745'))
            painter.drawText(col*200, row*230+205, 200, 20, Qt.AlignmentFlag.AlignCenter, f'{t:.2f} s')
    painter.end()
    canvas.save(str(root/'unified-motion-review.png'))
