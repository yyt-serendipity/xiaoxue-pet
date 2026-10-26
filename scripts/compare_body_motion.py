"""Offline actual-widget previews; no private config, network, or user desktop capture."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run_probe(baseline, output, label):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    sys.path.insert(0, str(ROOT))
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QBuffer, QIODevice
    import psutil
    from compare_motion import animated_png
    path = baseline if label == 'before' else ROOT/'桌宠.py'
    spec = importlib.util.spec_from_file_location('window_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SPRITE_DIR = str(ROOT/'sprites-anime')
    module.current_avoidance_reason = lambda *args: ''
    app = QApplication([])
    cases = ('idle', 'walk_stop', 'jump')
    times, memory = [], []
    with tempfile.TemporaryDirectory(prefix='pet-render-') as temporary:
        module.APP_DIR = temporary
        module.CONFIG_PATH = str(Path(temporary)/'config.json')
        pet = module.PetWindow()
        pet.timer.stop()
        pet.tray.hide()
        pet.set_mode('still')
        pet.set_size(.55)
        pet.bubble_text = ''
        pet.show()
        app.processEvents()
        clock = [0.]
        pet.animator.clock = lambda: clock[0]
        pet.animator.timeline.clock = lambda: clock[0]

        def sample_case(case, export=False):
            from body_motion import BodyMotion
            pet.animator.clear_transient()
            pet.animator.last_identity = None
            pet.animator.timeline.action = None
            pet.animator.timeline.last = 0.
            pet.animator.timeline.next_blink = 100.
            pet.animator.timeline.blink_started = None
            if hasattr(pet, 'body_motion'):
                pet.body_motion = BodyMotion()
            frames = []
            next_draw, pix = 0., None
            for index in range(160):
                presentation_time = index*.02
                # Simulate each version's scheduling; this is not real-time FPS measurement.
                while next_draw <= presentation_time + 1e-9:
                    clock[0] = next_draw
                    pet.t = next_draw/.02
                    walking = case == 'walk_stop' and .3 <= next_draw < 1.8
                    pet.target = (1000, 200) if walking else None
                    pet.dir = 'left' if case == 'walk_stop' else 'down'
                    pet.facing = 1
                    pet.cur_speed = min(160., (next_draw-.3)*800) if walking else 0.
                    pet.jump_t = max(0., 1-(next_draw-.5)*3) if case == 'jump' and next_draw >= .5 else 0.
                    start = time.perf_counter()
                    pix = pet.grab()
                    if not export:
                        times.append((time.perf_counter()-start)*1000)
                    active = walking or pet.jump_t > 0 or (hasattr(pet,'body_motion') and pet.body_motion.walk_weight > .01)
                    next_draw += .02 if active else .05 if label == 'before' else .033
                if export:
                    buffer = QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    pix.save(buffer,'PNG'); frames.append(bytes(buffer.data()))
            if export:
                animated_png(frames, output/f'{label}-{case}.png')
                (output/f'{label}-{case}-still.png').write_bytes(frames[0])
            else:
                info = psutil.Process().memory_info()
                memory.append({'case':case,'working_set_mib':round(info.rss/2**20,2),'private_mib':round(info.private/2**20,2)})
            assert pet.animator.cache_bytes <= 2*1024*1024
            for group in pet.animator.frames.values():
                for bank in group.values():
                    if hasattr(bank,'resident'): assert len(bank.resident) <= 2

        for case in cases:
            sample_case(case)
        report = {'scope':'actual Qt widget grab, offscreen, temporary settings; excludes Windows compositor and game FPS',
                  'height':187,'sampled_duration_per_case_s':3.2,
                  'draw_p95_ms':round(sorted(times)[int(len(times)*.95)],3),
                  'draw_median_ms':round(statistics.median(times),3),'working_set_snapshots':memory,
                  'source_frame_limit':2,'blend_cache_mib':2,'runtime_optical_flow':False}
        assert 'cv2' not in sys.modules and 'numpy' not in sys.modules
        (output/f'{label}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report),flush=True)
        for case in cases:
            sample_case(case,export=True)
        pet.hide(); pet.tray.hide(); pet.deleteLater(); app.processEvents()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/body-motion')
    parser.add_argument('--renderer',choices=('before','after'))
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    if args.renderer:
        run_probe(args.baseline.resolve(),output,args.renderer);return
    for label in ('before','after'):
        subprocess.run([sys.executable,__file__,'--baseline',str(args.baseline.resolve()),'--output',str(output),'--renderer',label],check=True)
    (output/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>整体动效对比</title>
<style>body{font:16px system-ui;background:#f4f1ed;color:#334454;margin:32px}main{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0;background:white;border-radius:16px;padding:18px;text-align:center}img{display:block;max-width:100%;height:320px}select,button{font:inherit;padding:9px 16px;margin:12px 12px 18px 0}p{max-width:850px;line-height:1.7}</style>
<h1>整体动效 · 前后对比</h1><p>相同人物素材，实际 Qt 控件离线渲染。对比呼吸、行走起停与跳跃；不代表原大肥鱼程序实录，也不是游戏 FPS 测试。</p>
<select id="pick"><option value="idle">待机呼吸</option><option value="walk_stop">开始走路 → 停下</option><option value="jump">轻轻跳跃</option></select><button id="toggle">暂停</button>
<main><figure><img id="before"><figcaption>调整前</figcaption></figure><figure><img id="after"><figcaption>当前版</figcaption></figure></main>
<p>整个人物微幅变换，没有拆分肢体；既有手部原画和光流中间帧未改动。位移的小数累计在实际窗口移动时生效，这个固定镜头预览不展示屏幕位移。</p>
<script>let paused=false;let pick=document.getElementById('pick'),button=document.getElementById('toggle');function show(){for(let id of ['before','after'])document.getElementById(id).src=id+'-'+pick.value+(paused||document.hidden?'-still':'')+'.png'}pick.onchange=show;button.onclick=()=>{paused=!paused;button.textContent=paused?'播放':'暂停';show()};document.addEventListener('visibilitychange',show);show();</script>''',encoding='utf-8')


if __name__=='__main__':main()
