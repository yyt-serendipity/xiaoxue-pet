"""Measure isolated renderers and export native 50 fps APNG motion comparisons."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import struct
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data) & 0xffffffff)


def animated_png(frames, path):
    # Package the actual Qt-rendered PNG frames; no character redrawing.
    output = bytearray(b'\x89PNG\r\n\x1a\n')
    sequence = 0
    for index, frame in enumerate(frames):
        pos, payloads, header = 8, [], None
        while pos < len(frame):
            length = struct.unpack('>I', frame[pos:pos+4])[0]
            kind, data = frame[pos+4:pos+8], frame[pos+8:pos+8+length]
            if kind == b'IHDR':
                header = data
            elif kind == b'IDAT':
                payloads.append(data)
            pos += length+12
        width, height = struct.unpack('>II', header[:8])
        if index == 0:
            output += chunk(b'IHDR', header)
            output += chunk(b'acTL', struct.pack('>II', len(frames), 0))
        output += chunk(b'fcTL', struct.pack('>IIIIIHHBB', sequence, width, height, 0, 0, 1, 50, 0, 0))
        sequence += 1
        for data in payloads:
            output += chunk(b'IDAT', data) if index == 0 else chunk(b'fdAT', struct.pack('>I', sequence)+data)
            if index:
                sequence += 1
    output += chunk(b'IEND', b'')
    path.write_bytes(output)


def measure(module_file, label, output):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    sys.path.insert(0, str(ROOT))
    import psutil
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QBuffer, QIODevice
    from sprite_store import SpriteStore
    spec = importlib.util.spec_from_file_location('measured_animation', module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = QApplication([])
    sprites = SpriteStore(ROOT/'sprites-anime', 238)
    results, times = {}, []
    for pose in ('walk1', 'wave', 'drink'):
        clock = [0.]
        animator = module.Animator(ROOT/'sprites-anime', [238], clock=lambda: clock[0])
        animator.timeline.rate = 1.5
        previous, repeats = None, 0
        for index in range(160):
            clock[0] = index*.02
            start = time.perf_counter()
            frame = animator.render((pose, 238, 1), sprites, 100 if pose == 'walk1' else 0)
            times.append((time.perf_counter()-start)*1000)
            rendered = frame.toImage()
            digest = hashlib.sha256(bytes(rendered.bits())).digest()
            repeats += int(previous == digest)
            previous = digest
            assert animator.cache_bytes <= 2*1024*1024
            for bank in animator.frames.values():
                if hasattr(bank[238], 'resident'):
                    assert len(bank[238].resident) <= 2
        results[pose] = {'repeated_samples_of_159': repeats}
        animator.release()
    memory = psutil.Process().memory_info()
    report = {'actions': results, 'render_p95_ms': round(sorted(times)[int(len(times)*.95)], 3),
              'render_median_ms': round(statistics.median(times), 3),
              'working_set_mib': round(memory.rss/2**20, 2), 'private_mib': round(memory.private/2**20, 2),
              'cache_limit_mib': 2, 'sample_interval_ms': 20,
              'measurement_scope': 'renderer only, not full app or game FPS'}
    assert 'cv2' not in sys.modules and 'numpy' not in sys.modules
    (output/f'{label}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    # Export after measuring; encoder buffers are not desktop pet resident memory.
    for pose in ('walk1', 'wave', 'drink'):
        clock = [0.]
        animator = module.Animator(ROOT/'sprites-anime', [187], clock=lambda: clock[0])
        animator.timeline.rate = 1.5
        sprites = SpriteStore(ROOT/'sprites-anime', 187)
        frames = []
        for index in range(160):
            clock[0] = index*.02
            pix = animator.render((pose, 187, 1), sprites, 100 if pose == 'walk1' else 0)
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(buffer, 'PNG')
            frames.append(bytes(buffer.data()))
        animated_png(frames, output/f'{label}-{pose}.png')
        (output/f'{label}-{pose}-still.png').write_bytes(frames[0])
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'motion-comparison')
    parser.add_argument('--renderer', choices=('before', 'after'))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.renderer:
        measure(args.baseline if args.renderer == 'before' else ROOT/'animation.py', args.renderer, output)
        return
    for renderer in ('before', 'after'):
        subprocess.run([sys.executable, __file__, '--baseline', str(args.baseline.resolve()),
                        '--output', str(output), '--renderer', renderer], check=True)
    (output/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>动作优化对比</title>
<style>body{font:16px system-ui;margin:36px;background:#f5f2ed;color:#363c45}main{display:flex;gap:20px;flex-wrap:wrap}figure{margin:0;background:white;padding:24px;border-radius:16px;text-align:center}img{display:block;width:196px;height:187px}button,select{font:inherit;margin:0 12px 24px 0;padding:8px 16px}</style>
<h1>动作优化对比</h1><p>相同原画、相同尺寸与速度，由实际动画器以 50 帧/秒采样；不代表原画数量，也不是游戏性能测试。</p>
<select id="action"><option value="walk1">走路</option><option value="wave">挥手</option><option value="drink">喝水</option></select><button id="pause">暂停</button>
<main><figure><img id="before"><figcaption>原播放方式</figcaption></figure><figure><img id="after"><figcaption>离线中间帧播放</figcaption></figure></main>
<p>仍使用完整人物；快速抬手或遮挡变化可能残留补帧重影。按动作比较，不把帧数等同于动作质量。</p>
<script>let paused=false;const pick=document.getElementById('action'),btn=document.getElementById('pause');function show(){for(const side of ['before','after'])document.getElementById(side).src=side+'-'+pick.value+(paused||document.hidden?'-still':'')+'.png'}pick.onchange=show;btn.onclick=()=>{paused=!paused;btn.textContent=paused?'播放':'暂停';show()};document.addEventListener('visibilitychange',show);show();</script>''', encoding='utf-8')


if __name__ == '__main__':
    main()
