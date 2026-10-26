"""Offline whole-character inbetweens for walk, wave and drink; never a runtime import."""
import json
from pathlib import Path
from build_heart_motion import cv2, np, gray, premultiply, morph

ROOT = Path(__file__).parent
STEPS = 8
SOURCES = {
    'walk': ('walk-cycle', [(i, (i + 1) % 8) for i in range(8)]),
    'wave': ('wave-cycle', [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 1)]),
    'drink': ('drink', [(0, 1), (1, 2), (2, 3)]),
}


def build():
    prepared = ROOT/'sprites-anime/prepared'
    for action, (folder, edges) in SOURCES.items():
        frames = {}
        for index in sorted({i for pair in edges for i in pair}):
            data = (prepared/'306'/folder/f'{index}.png').read_bytes()
            frames[index] = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
        h, w = frames[0].shape[:2]
        x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        grid = np.stack((x, y), axis=-1)
        manifest = {'version': 1, 'count': len(edges)*(STEPS+1), 'edges': {}, 'keyframes': {}}
        for edge, (first, second) in enumerate(edges):
            offset = edge*(STEPS+1)
            manifest['edges'][f'{first}:{second}'] = [offset, STEPS]
            manifest['keyframes'].setdefault(str(first), offset)
            manifest['keyframes'].setdefault(str(second), offset+STEPS)
            a, b = frames[first], frames[second]
            dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
            forward = dis.calc(gray(a), gray(b), None)
            backward = dis.calc(gray(b), gray(a), None)
            pa, pb = premultiply(a), premultiply(b)
            for step in range(STEPS+1):
                frame = a if step == 0 else b if step == STEPS else morph(pa, pb, forward, backward, step/STEPS, grid)
                for height in (119, 187, 238, 306):
                    dest = prepared/str(height)/'action-motion'/action
                    dest.mkdir(parents=True, exist_ok=True)
                    image = frame if height == 306 else cv2.resize(frame, (round(height*1.05), height), interpolation=cv2.INTER_AREA)
                    ok, encoded = cv2.imencode('.png', image)
                    if not ok:
                        raise RuntimeError('PNG encoding failed')
                    (dest/f'{offset+step}.png').write_bytes(encoded.tobytes())
        for height in (119, 187, 238, 306):
            (prepared/str(height)/'action-motion'/action/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        print(f'{action}: {manifest["count"]} disk frames, two decoded frames at runtime', flush=True)


if __name__ == '__main__':
    build()
