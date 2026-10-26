"""Time-based sprite playback, aligned feet, blink isolation and pose transitions."""
import math
import random
import time
import json
from collections import OrderedDict
from pathlib import Path
from sprite_store import EXTRA_ACTIONS, read_pixmap

HEART_ACTIONS = EXTRA_ACTIONS[:3]
HEART_DURATION = 3.6

def smoothstep(value):
    value = max(0., min(1., value))
    return value * value * (3. - 2. * value)

def heart_sample(age):
    # Ease the whole lift/lower path, not each individual frame boundary.
    if age < 1.15:
        value = smoothstep(age / 1.15) * 4
        i = min(3, int(value))
        return i, i + 1, value - i
    if age < 1.5:
        return 4, 4, 0.
    if age < 1.7:
        return 4, 5, smoothstep((age - 1.5) / .2)
    if age < 1.85:
        return 5, 5, 0.
    if age < 2.05:
        return 5, 4, smoothstep((age - 1.85) / .2)
    if age < 3.4:
        sequence = (4, 3, 2, 1, 0)
        value = smoothstep((age - 2.05) / 1.35) * 4
        i = min(3, int(value))
        return sequence[i], sequence[i + 1], value - i
    return 0, 0, 0.

class FramePair:
    """Decode at most the two source frames needed for the current blend."""
    def __init__(self, directory, count):
        self.directory, self.count = Path(directory), count
        self.resident = {}

    def select(self, first, second):
        wanted = {first, second}
        for index in list(self.resident):
            if index not in wanted:
                del self.resident[index]
        for index in wanted:
            self[index]

    def __getitem__(self, index):
        if not 0 <= index < self.count:
            raise IndexError(index)
        if index not in self.resident:
            if len(self.resident) >= 2:
                del self.resident[next(iter(self.resident))]
            self.resident[index] = read_pixmap(self.directory / f'{index}.png')
        return self.resident[index]

    def __len__(self):
        return self.count


class MotionBank(FramePair):
    """Translate authored pose pairs to offline inbetweens without loading a sheet."""
    def __init__(self, directory):
        data = json.loads((Path(directory)/'manifest.json').read_text(encoding='utf-8'))
        super().__init__(directory, data['count'])
        self.edges, self.keyframes = data['edges'], data['keyframes']

    def resolve(self, first, second, fraction):
        fraction = min(1., max(0., fraction))
        edge = self.edges.get(f'{first}:{second}')
        if edge is None:
            edge = self.edges.get(f'{second}:{first}')
            if edge is not None:
                fraction = 1. - fraction
        if edge is None:
            # Identical poses and a rare stop from a nonadjacent walk phase.
            return self.keyframes[str(first)], self.keyframes[str(second)], fraction
        start, steps = edge
        position = start + fraction*steps
        index = min(start+steps, int(position))
        return index, min(start+steps, index+1), position-index


from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBitmap, QImage, QPainter, QPixmap, QRegion


def alpha_bounds(image):
    return QRegion(QBitmap.fromImage(image.createAlphaMask())).boundingRect()


def load_frames(path, columns, rows, heights):
    path = Path(path)
    prepared = path.parent / 'prepared'
    from sprite_store import read_pixmap
    if (prepared / 'manifest.json').exists():
        return {h:[read_pixmap(prepared / str(h) / path.stem / f'{i}.png')
                   for i in range(columns * rows)] for h in heights}
    return load_frames_raw(path, columns, rows, heights)


def load_frames_raw(path, columns, rows, heights):
    image = QImage(str(path))
    if image.isNull() or not image.hasAlphaChannel():
        raise RuntimeError(f'动画素材缺失或没有透明通道: {path}')
    frames = {h: [] for h in heights}
    for index in range(columns * rows):
        row, col = divmod(index, columns)
        x0, x1 = round(col * image.width() / columns), round((col + 1) * image.width() / columns)
        y0, y1 = round(row * image.height() / rows), round((row + 1) * image.height() / rows)
        cell = image.copy(x0, y0, x1 - x0, y1 - y0)
        bounds = alpha_bounds(cell)
        if bounds.isEmpty():
            raise RuntimeError(f'动画帧为空: {path}, {index}')
        # Align by the stable hat band, not a waving hand or the changing leg spread.
        band_y = bounds.top() + round(bounds.height() * .10)
        band = alpha_bounds(cell.copy(0, band_y, cell.width(), round(bounds.height() * .10)))
        anchor = band.center().x() if not band.isEmpty() else bounds.center().x()
        for h in heights:
            canvas = QPixmap(round(h * 1.05), h)
            canvas.fill(Qt.GlobalColor.transparent)
            scale = h * .93 / bounds.height()
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(QRectF(canvas.width() / 2 + (bounds.left() - anchor) * scale,
                                     h * .97 - bounds.height() * scale,
                                     bounds.width() * scale, bounds.height() * scale), cell, QRectF(bounds))
            painter.end()
            frames[h].append(canvas)
    return frames


def blend(first, second, fraction):
    if first.cacheKey() == second.cacheKey():
        return first
    if fraction <= 0:
        return first
    if fraction >= 1:
        return second
    output = QPixmap(first.size())
    output.fill(Qt.GlobalColor.transparent)
    painter = QPainter(output)
    # Add premultiplied layers, avoiding the dim halo from two source-over passes.
    painter.setOpacity(1 - fraction)
    painter.drawPixmap(0, 0, first)
    painter.end()
    weighted = QPixmap(first.size())
    weighted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(weighted)
    painter.setOpacity(fraction)
    painter.drawPixmap(0, 0, second)
    painter.end()
    painter = QPainter(output)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    painter.drawPixmap(0, 0, weighted)
    painter.end()
    return output


class MotionClock:
    def __init__(self, clock=time.monotonic, rng=None):
        self.clock, self.rng = clock, rng or random.Random()
        self.last = self.clock()
        self.action_started = self.last
        self.action = None
        self.phase = 0.
        self.next_blink = self.last + self.rng.uniform(3., 6.)
        self.blink_started = None
        self.rate = 1.
        self.settle_from = 0
        self.settle_to = 2

    def sample(self, action, speed, height):
        now = self.clock()
        dt = min(.1, max(0., now - self.last))
        self.last = now
        if action != self.action:
            if action == 'settle':
                self.settle_from = int(self.phase * 8) % 8
                self.settle_to = 2 if self.phase < .5 else 6
            self.action, self.action_started = action, now
            self.phase = 0.
            self.blink_started = None
        if action == 'settle':
            return self.settle_from, self.settle_to, min(1., (now - self.action_started) / .16)
        if action == 'walk':
            self.phase = (self.phase + dt * max(0., speed) / max(1., height * .9)) % 1.
            value = self.phase * 8
            return int(value), (int(value) + 1) % 8, value % 1
        if action in HEART_ACTIONS:
            return heart_sample((now - self.action_started) * self.rate)
        if action in EXTRA_ACTIONS:
            sequence = [0, 1, 2, 3, 3, 2, 1, 0, 0]
            value = min((now - self.action_started) * self.rate / .38, len(sequence) - 1.)
            i = int(value)
            return sequence[i], sequence[min(i + 1, len(sequence) - 1)], value % 1
        if action == 'wave':
            # Lift -> wrist oscillation -> lower -> settle. No abrupt loop restart.
            sequence = [0, 1, 2, 3, 4, 3, 4, 3, 4, 5, 1, 0, 0, 0]
            value = min((now - self.action_started) * self.rate / .22, len(sequence) - 1.)
            i = int(value)
            return sequence[i], sequence[(i + 1) % len(sequence)], value % 1
        if action == 'idle':
            if self.blink_started is None and now >= self.next_blink:
                self.blink_started = now
            if self.blink_started is not None:
                age = now - self.blink_started
                if age >= .28:
                    self.blink_started = None
                    self.next_blink = now + self.rng.uniform(3., 6.)
                else:
                    sequence = [0, 1, 2, 2, 3, 0]
                    value = age / .28 * 5
                    i = int(value)
                    return sequence[i], sequence[i + 1], value % 1
        return 0, 0, 0.


class Animator:
    def __init__(self, directory, heights, clock=time.monotonic):
        self.directory = Path(directory)
        self.frames = {}
        self.loaded_height = None
        self.timeline = MotionClock(clock)
        self.clock = clock
        self.last_identity = None
        self.last_frame = self.previous = None
        self.transition_started = 0.
        self.transition_duration = .12
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.cache_budget = 2 * 1024 * 1024
        self.ensure_height(list(heights)[0])

    def clear_transient(self):
        self.cache.clear()
        self.cache_bytes = 0
        self.last_frame = self.previous = None

    def release(self):
        self.clear_transient()
        self.frames.clear()
        self.loaded_height = None
        self.last_identity = None

    def ensure_height(self, height):
        if height == self.loaded_height:
            return
        self.clear_transient()
        self.frames.clear()
        self.frames = {
            'walk': {height:FramePair(self.directory / 'prepared' / str(height) / 'walk-cycle', 8)},
            'wave': {height:FramePair(self.directory / 'prepared' / str(height) / 'wave-cycle', 6)},
            'idle': load_frames(self.directory / 'blink-cycle.png', 4, 1, [height]),
        }
        for action in ('walk', 'wave'):
            directory = self.directory/'prepared'/str(height)/'action-motion'/action
            if (directory/'manifest.json').is_file():
                self.frames[action] = {height: MotionBank(directory)}
        # Hold the entire body still during blinking; only replace the eye/glasses strip.
        for h, frames in self.frames['idle'].items():
            base = frames[0]
            for i in range(1, len(frames)):
                combined = QPixmap(base)
                painter = QPainter(combined)
                painter.setClipRect(0, round(h * .25), base.width(), round(h * .17))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, frames[i])
                painter.end()
                frames[i] = combined
        self.loaded_height = height

    def remember(self, key, pix):
        self.cache[key] = pix
        self.cache_bytes += pix.width() * pix.height() * 4
        while self.cache_bytes > self.cache_budget and self.cache:
            _, old = self.cache.popitem(last=False)
            self.cache_bytes -= old.width() * old.height() * 4
        return pix

    def render(self, key, sprites, speed):
        name, h, facing = key
        self.ensure_height(h)
        action = 'walk' if name in ('walk1', 'walk2') else 'wave' if name == 'wave' else 'idle' if name == '正面' else name
        for base in ('walk', 'wave'):
            if action != base and not (base == 'walk' and action == 'settle'):
                self.frames[base][h].resident.clear()
        for extra in EXTRA_ACTIONS:
            if extra != action:
                self.frames.pop(extra, None)
        if action in EXTRA_ACTIONS and action not in self.frames:
            motion_ready = (self.directory / 'prepared' / str(h) / 'heart-motion' / action / '40.png').is_file()
            folder = ('heart-motion' if motion_ready else 'heart-smooth') if action in HEART_ACTIONS else ''
            count = (41 if motion_ready else 8) if action in HEART_ACTIONS else 4
            self.frames[action] = {h:FramePair(self.directory / 'prepared' / str(h) / folder / action, count)}
            directory = self.directory/'prepared'/str(h)/'action-motion'/action
            if (directory/'manifest.json').is_file():
                self.frames[action] = {h: MotionBank(directory)}
        first, second, fraction = self.timeline.sample(action, speed, h)
        bank = self.frames.get('walk' if action == 'settle' else action, {}).get(h)
        offline_motion = isinstance(bank, MotionBank)
        if offline_motion:
            first, second, fraction = bank.resolve(first, second, fraction)
        if action in HEART_ACTIONS and self.frames[action][h].count == 41:
            # Motion-aware inbetweens were compiled offline, never computed here.
            position = (first + (second - first) * fraction) * 8
            first = min(40, int(position))
            second = min(40, first + 1)
            fraction = position - first
        if action == 'walk' and not offline_motion:
            fraction = max(0., (fraction - .8) / .2)
        steps = 32 if action in HEART_ACTIONS or offline_motion else 12
        fraction = round(fraction * steps) / steps
        if action in EXTRA_ACTIONS or action in ('walk', 'wave', 'settle'):
            self.frames['walk' if action == 'settle' else action][h].select(first, second)
        # Same cached frame for idle/held poses; mirrored and blended frames are bounded.
        source_key = None if action in self.frames or action == 'settle' else sprites[(name, h)].cacheKey()
        cache_key = (action, h, facing, first, second, fraction, source_key)
        current = self.cache.get(cache_key)
        if current is not None:
            self.cache.move_to_end(cache_key)
        else:
            current = self.make_frame(action, name, h, facing, first, second, fraction, sprites)
            self.remember(cache_key, current)
        identity = (action, h, facing)
        now = self.clock()
        if identity != self.last_identity:
            self.transition_duration = .2 if action in HEART_ACTIONS or (self.last_identity and self.last_identity[0] in HEART_ACTIONS) else .12
            self.previous = self.last_frame if self.last_frame is not None and self.last_frame.size() == current.size() else None
            self.transition_started, self.last_identity = now, identity
        age = (now - self.transition_started) / self.transition_duration
        if self.previous is not None and age < 1:
            current = blend(self.previous, current, max(0., age) ** 2 * (3 - 2 * max(0., age)))
        elif age >= 1:
            self.previous = None
        self.last_frame = current
        return current

    def make_frame(self, action, name, h, facing, first, second, fraction, sprites):
        if action in self.frames or action == 'settle':
            frames = self.frames['walk' if action == 'settle' else action][h]
            # Smooth time interpolation between authored intermediate poses.
            # Offline banks already contain spatial inbetweens; do not ease each tiny step.
            ease = fraction if action in HEART_ACTIONS or isinstance(frames, MotionBank) else smoothstep(fraction)
            current = blend(frames[first], frames[second], ease)
        else:
            current = QPixmap(round(h * 1.05), h)
            current.fill(Qt.GlobalColor.transparent)
            pix = sprites[(name, h)]
            painter = QPainter(current)
            painter.drawPixmap((current.width() - pix.width()) // 2, h - pix.height(), pix)
            painter.end()
        if facing < 0:
            current = QPixmap.fromImage(current.toImage().mirrored(True, False))
        return current
