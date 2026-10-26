"""Render source-asset previews using the real animation player, without personal state."""
from pathlib import Path
import argparse
import html
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    sys.path.insert(0, str(root))
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontDatabase
    from animation import Animator
    from sprite_store import SpriteStore
    app = QApplication([])
    if os.name == 'nt':
        font = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts/msyh.ttc'
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
    poses = [('正面', '站立'), ('wave', '挥手'), ('heart_finger', '指尖比心'),
             ('heart_chest', '胸前比心'), ('heart_overhead', '头顶比心'),
             ('drink', '喝水'), ('read', '看书'), ('eat', '蛋糕'),
             ('shy', '害羞'), ('stretch', '伸懒腰'), ('sit', '坐着'), ('sleep', '睡觉')]
    canvas = QImage(840, 700, QImage.Format.Format_ARGB32)
    canvas.fill(QColor('#f5f2ed'))
    painter = QPainter(canvas)
    painter.setFont(QFont('Microsoft YaHei UI', 11))
    for index, (pose, label) in enumerate(poses):
        frame = QImage(str(root/f'sprites-anime/prepared/187/{pose}.png'))
        if frame.isNull():
            raise RuntimeError(f'Missing {pose}; validate and compile first')
        x, y = (index % 4)*210, (index//4)*230
        painter.drawImage(x+7, y+10, frame)
        painter.setPen(QColor('#393a42'))
        painter.drawText(x+16, y+220, label)
    painter.end()
    canvas.save(str(root/'pet-preview.png'))
    actions = [('wave','挥手'),('heart_finger','指尖比心'),('heart_chest','胸前比心'),
               ('heart_overhead','头顶比心'),('drink','喝水'),('walk1','走路'),('正面','眨眼')]
    cards = []
    for pose, label in actions:
        clock = [0.]
        animator = Animator(root/'sprites-anime', [187], clock=lambda: clock[0])
        animator.timeline.rate = 1.5
        animator.timeline.next_blink = .6
        sprites = SpriteStore(root/'sprites-anime', 187)
        destination = root/'pet-preview-frames'/pose
        destination.mkdir(parents=True, exist_ok=True)
        for index in range(40):
            clock[0] = index*.08
            pixmap = animator.render((pose, 187, 1), sprites, 65 if pose == 'walk1' else 0)
            if not pixmap.save(str(destination/f'{index}.png')):
                raise RuntimeError('Preview write failed')
            if animator.cache_bytes > 2*1024*1024:
                raise RuntimeError('Animation cache limit exceeded')
        cards.append(f'<figure><img width="196" height="187" data-pose="{html.escape(pose)}" src="pet-preview-frames/{pose}/0.png"><figcaption>{label}</figcaption></figure>')
    page = '''<!doctype html><meta charset="utf-8"><title>桌宠动作预览</title>
<style>body{font:16px system-ui;background:#f5f2ed;color:#393a42;margin:32px}main{display:flex;flex-wrap:wrap;gap:12px}figure{margin:0;padding:18px;background:#fff;border-radius:16px;text-align:center}button{padding:8px 20px;margin-bottom:20px}img{display:block}</style>
<h1>桌宠动作预览</h1><p>真实动画器采样 · 中号 187 像素 · 1.5 倍动作速度；这是素材预览，不是桌面截图。</p>
<button id="toggle">暂停</button><main>''' + ''.join(cards) + '''</main>
<script>let frame=0,paused=false;const btn=document.getElementById('toggle');btn.onclick=()=>{paused=!paused;btn.textContent=paused?'播放':'暂停'};setInterval(()=>{if(paused||document.hidden)return;frame=(frame+1)%40;document.querySelectorAll('img[data-pose]').forEach(img=>img.src='pet-preview-frames/'+img.dataset.pose+'/'+frame+'.png')},80)</script>'''
    (root/'pet-preview.html').write_text(page, encoding='utf-8')
    print(json.dumps({'overview':str(root/'pet-preview.png'),'animation':str(root/'pet-preview.html'),
                      'note':'Keep pet-preview-frames beside the HTML when sharing.'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
