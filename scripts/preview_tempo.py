"""Compare current runtime tempos using real Qt widget renders and isolated settings."""
from pathlib import Path
import importlib.util
import json
import os
import sys
import tempfile
import time
import statistics

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    sys.path.insert(0, str(ROOT))
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QBuffer, QIODevice
    import psutil
    from body_motion import BodyMotion
    from compare_motion import animated_png
    spec = importlib.util.spec_from_file_location('tempo_pet', ROOT/'桌宠.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.current_avoidance_reason = lambda *args: ''
    output = ROOT/'docs/tempo'
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    cases = ('idle', 'walk', 'wave', 'heart_finger', 'heart_chest', 'heart_overhead')
    clock = [0.]
    reports = []
    with tempfile.TemporaryDirectory(prefix='pet-tempo-') as temporary:
        module.APP_DIR = temporary
        module.CONFIG_PATH = str(Path(temporary)/'config.json')
        pet = module.PetWindow()
        pet.timer.stop(); pet.tray.hide()
        pet.set_mode('still'); pet.set_size(.55)
        pet.bubble_text = ''
        pet.companion.clock = lambda: clock[0]
        pet.animator.clock = lambda: clock[0]
        pet.animator.timeline.clock = lambda: clock[0]
        pet.show(); app.processEvents()

        def reset(case, rate):
            clock[0] = 0.
            pet.companion.wake()
            pet.companion.pose = None
            pet.companion.data['motion_rate'] = rate
            if case not in ('idle', 'walk'):
                pet.perform_pose(case)
            pet.bubble_text = ''
            pet.target = (1000, 200) if case == 'walk' else None
            pet.dir = 'left' if case == 'walk' else 'down'
            pet.facing = 1
            pet.cur_speed = 140*rate if case == 'walk' else 0.
            pet.jump_t = pet.action_t = 0.
            pet.action = None
            pet.body_motion = BodyMotion()
            pet.animator.clear_transient()
            pet.animator.last_identity = None
            pet.animator.timeline.action = None
            pet.animator.timeline.last = 0.
            pet.animator.timeline.blink_started = None
            pet.animator.timeline.next_blink = 100.

        for rate, label in ((1., 'natural'), (.75, 'gentle')):
            times, memory = [], []
            # Measure before retaining PNG encoder buffers; excludes encoder and game FPS.
            for case in cases:
                reset(case, rate)
                for index in range(260):
                    clock[0] = index*.02
                    pet.t = clock[0]/.02
                    start = time.perf_counter()
                    pet.grab()
                    times.append((time.perf_counter()-start)*1000)
                    assert pet.animator.cache_bytes <= 2*1024*1024
                    for sizes in pet.animator.frames.values():
                        for bank in sizes.values():
                            if hasattr(bank, 'resident'):
                                assert len(bank.resident) <= 2
                memory.append(psutil.Process().memory_info().rss/2**20)
            reports.append(dict(rate=rate, draw_p95_ms=round(sorted(times)[int(len(times)*.95)],3),
                                draw_median_ms=round(statistics.median(times),3),
                                working_set_range_mib=[round(min(memory),2),round(max(memory),2)]))
        report = dict(scope='current Qt widget, offscreen, same code, fixed 20ms sampling, no encoder buffers; not runtime scheduler or game FPS',
                      height=187, duration_s=5.2, frames=260, source_frame_limit=2,
                      blend_cache_mib=2, results=reports)
        (output/'measurement.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        assert 'cv2' not in sys.modules and 'numpy' not in sys.modules
        for rate, label in ((1., 'natural'), (.75, 'gentle')):
            for case in cases:
                reset(case, rate)
                frames=[]
                for index in range(260):
                    clock[0] = index*.02
                    pet.t = clock[0]/.02
                    pix = pet.grab()
                    buffer=QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    pix.save(buffer,'PNG'); frames.append(bytes(buffer.data()))
                animated_png(frames,output/f'{label}-{case}.png')
                (output/f'{label}-{case}-still.png').write_bytes(frames[0])
        pet.hide(); pet.tray.hide(); pet.deleteLater(); app.processEvents()
    (output/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>舒缓动作对比</title>
<style>body{font:16px system-ui;background:#f5f2ed;color:#334454;margin:32px}main{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0;background:white;border-radius:18px;padding:18px;text-align:center}img{display:block;max-width:100%;height:320px}select,button{font:inherit;padding:9px 16px;margin:12px 12px 18px 0}p{max-width:850px;line-height:1.8}</style>
<h1>慢一点，自然一点</h1><p>同一版程序、同一套人物原画，比较 1× 与新的默认 0.75×。每轮 5.2 秒，实际 Qt 控件离线采样。比心和挥手包含完整抬手、停留与收手。</p>
<select id="pick"><option value="wave">挥挥手</option><option value="heart_finger">指尖比心</option><option value="heart_chest">双手比心</option><option value="heart_overhead">头顶大心</option><option value="walk">慢慢走</option><option value="idle">待机呼吸</option></select><button id="toggle">暂停</button>
<main><figure><img id="natural"><figcaption>自然 · 1×</figcaption></figure><figure><img id="gentle"><figcaption>舒缓 · 0.75×（默认）</figcaption></figure></main>
<p>新档位比 1× 慢 25%，一个动作的时长增加约 33%。没有增加运行素材或缓存。此页统一按 20ms 采样便于比较速度；程序仍使用原来的动态调度，实际游戏性能未测量。眨眼和提醒计时保持自然节奏；既有补帧重影仍可能存在。</p>
<script>let paused=false;let pick=document.getElementById('pick'),button=document.getElementById('toggle');function show(){for(let id of ['natural','gentle'])document.getElementById(id).src=id+'-'+pick.value+(paused||document.hidden?'-still':'')+'.png'}pick.onchange=show;button.onclick=()=>{paused=!paused;button.textContent=paused?'播放':'暂停';show()};document.addEventListener('visibilitychange',show);show();</script>''',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
