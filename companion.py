"""Local companion state, action atlas, and controls. No network access."""
import json
import math
import os
import time
import random
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QSpinBox,
    QTabWidget, QToolButton, QVBoxLayout, QWidget, QScrollArea, QButtonGroup, QComboBox, QFrame)
from pet_theme import STYLE

POSES = {
    'wave': ('挥挥手', 0, 0.94), 'heart': ('比个心', 1, 0.94),
    'shy': ('害羞', 2, 0.94), 'happy': ('摸摸头', 3, 0.94),
    'read': ('一起看书', 4, 0.80), 'sit': ('坐一会儿', 5, 0.80),
    'sleep': ('睡个好觉', 6, 0.55), 'eat': ('吃块蛋糕', 7, 0.80),
    'walk1': ('迈步', 8, 0.94), 'walk2': ('收步', 9, 0.94),
    'stretch': ('伸个懒腰', 10, 0.94), 'lift': ('被提起来', 11, 0.94),
    'heart_finger': ('指尖比心', -1, .94), 'heart_chest': ('双手比心', -1, .94),
    'heart_overhead': ('头顶大心', -1, .94), 'drink': ('喝口水', -1, .94),
}
POSE_LINES = {'wave': '嗨，我在这里呀～', 'heart': '送你一颗小小的心～',
    'shy': '嘿嘿，有一点不好意思。', 'happy': '摸摸头，心情变好啦！',
    'read': '一起安静看一会儿书吧。', 'sit': '坐下来歇一会儿～',
    'sleep': '晚安，醒来再陪你。', 'eat': '一口蛋糕，一点快乐～',
    'stretch': '伸伸懒腰，肩膀放松～',
    'heart_finger': '给你一颗小小的心，今天也偏心你。',
    'heart_chest': '这颗心给你，忙完记得回来看看我。',
    'heart_overhead': '这么大一颗心，够不够装下你呀？',
    'drink': '我也喝一口，你的水杯在手边吗？'}


class CompanionState:
    """Timers use monotonic time; only preferences and care stats persist."""
    def __init__(self, path, clock=time.monotonic):
        self.path, self.clock = Path(path), clock
        self.data = dict(name='小薛同学', mood=80., energy=85., fullness=80.,
                         sessions=0, focus_minutes=0, quiet=False,
                         reminders=True, reminder_minutes=45, game_guard=True,
                         motion_rate=.75, avoidance_apps='')
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(saved, dict):
                for key, default in self.data.items():
                    value = saved.get(key, default)
                    if isinstance(value, type(default)) or (type(default) is float and type(value) is int):
                        self.data[key] = value
        except (OSError, ValueError):
            pass
        for key in ('mood', 'energy', 'fullness'):
            self.data[key] = self._bounded(self.data[key])
        self.data['name'] = self.data['name'].strip()[:12] or '小伴'
        self.data['reminder_minutes'] = max(1, min(240, self.data['reminder_minutes']))
        if self.data['motion_rate'] not in (.75, 1., 1.5, 2.):
            self.data['motion_rate'] = .75
        self.pose, self.pose_until, self.sleeping = None, 0, False
        self.phase, self.deadline, self.paused = None, None, None
        self.focus_duration = 0
        self.last_tick = self.clock()
        self.next_reminder = self.last_tick + self.data['reminder_minutes'] * 60
        self.reminder_index = 0
        self.last_reward = -1000.
        self.last_save = self.last_tick
        self.save_error = None
        self._saved_payload = None

    @staticmethod
    def _bounded(value):
        return max(0., min(100., value)) if math.isfinite(value) else 80.

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        try:
            payload = json.dumps(self.data, ensure_ascii=False, indent=2)
            if payload == self._saved_payload and self.path.exists():
                return True
            temporary.write_text(payload, encoding='utf-8')
            os.replace(temporary, self.path)
            self._saved_payload = payload
            self.save_error = None
        except OSError as exc:
            self.save_error = str(exc)
        return self.save_error is None

    def set_pose(self, pose, seconds=7):
        if pose not in POSES:
            return
        self.sleeping = pose == 'sleep'
        if self.sleeping:
            self.cancel_focus()
        self.pose, self.pose_until = pose, self.clock() + seconds
        if pose in ('happy', 'heart', 'eat') and self.clock() - self.last_reward >= 10:
            self.data['mood'] = self._bounded(self.data['mood'] + 5)
            if pose == 'eat':
                self.data['fullness'] = self._bounded(self.data['fullness'] + 15)
            self.last_reward = self.clock()

    def wake(self):
        self.sleeping, self.pose = False, None

    def current_pose(self):
        if self.sleeping:
            return 'sleep'
        if self.pose and self.clock() < self.pose_until:
            return self.pose
        if self.phase == 'focus':
            return 'read' if self.paused is None else 'sit'
        if self.phase == 'break':
            return 'sit'
        return None

    def start_focus(self, minutes=30, phase='focus'):
        self.wake()
        self.phase, self.paused = phase, None
        self.focus_duration = max(1, min(180, minutes))
        self.deadline = self.clock() + self.focus_duration * 60

    def remaining(self):
        if not self.phase:
            return 0
        return max(0, math.ceil(self.paused if self.paused is not None else self.deadline - self.clock()))

    def pause_focus(self):
        if not self.phase:
            return
        if self.paused is None:
            self.paused = max(0, self.deadline - self.clock())
        else:
            self.deadline, self.paused = self.clock() + self.paused, None

    def cancel_focus(self):
        self.phase, self.deadline, self.paused = None, None, None

    def configure_reminder(self, enabled, minutes):
        self.data['reminders'] = bool(enabled)
        self.data['reminder_minutes'] = max(1, min(240, int(minutes)))
        self.next_reminder = self.clock() + self.data['reminder_minutes'] * 60

    def tick(self, suppress_reminders=False):
        now = self.clock()
        minutes = min(60, max(0, now - self.last_tick)) / 60
        self.last_tick = now
        self.data['energy'] = self._bounded(self.data['energy'] + minutes * (2 if self.sleeping else -.12))
        self.data['fullness'] = self._bounded(self.data['fullness'] - minutes * .15)
        events = []
        if self.phase and self.paused is None and now >= self.deadline:
            phase = self.phase
            if phase == 'focus':
                self.data['sessions'] += 1
                self.data['focus_minutes'] += self.focus_duration
                self.data['mood'] = self._bounded(self.data['mood'] + 8)
            self.cancel_focus()
            self.set_pose('happy' if phase == 'focus' else 'stretch')
            events.append('focus_done' if phase == 'focus' else 'break_done')
            self.next_reminder = now + self.data['reminder_minutes'] * 60
            self.save()
        if not events and self.data['reminders'] and now >= self.next_reminder:
            # Wait until awake, not focusing and not quiet; deliver once, never a backlog.
            if not self.sleeping and not self.phase and not self.data['quiet'] and not suppress_reminders:
                events.append(('water', 'walk', 'eyes')[self.reminder_index % 3])
                self.reminder_index += 1
                self.next_reminder = now + self.data['reminder_minutes'] * 60
        if now - self.last_save >= 60:
            self.save()
            self.last_save = now
        return events


class CompanionPanel(QDialog):
    def __init__(self, pet):
        super().__init__(pet, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.pet = pet
        self.setWindowTitle('陪伴小屋')
        self.setMinimumWidth(400)
        self.resize(420, 460)
        layout = QVBoxLayout(self)
        self.setStyleSheet(STYLE + '\nQTabBar {background:transparent;} QTabBar::tab {padding:8px 17px;margin:0;border-radius:0;} QTabBar::tab:selected {background:transparent;border-bottom:2px solid #456c82;}')
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(10)
        tabs = self.tabs = QTabWidget()
        tabs.tabBar().setExpanding(True)
        tabs.tabBar().setMinimumWidth(380)
        layout.addWidget(tabs)
        def add_page(widget, title):
            widget.setObjectName('tabPage')
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
            tabs.addTab(scroll, title)
        actions = QWidget()
        grid = QGridLayout(actions)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(6)
        self.action_buttons = {}
        for i, key in enumerate(['read', 'drink', 'wave',
                                 'heart_finger', 'heart_chest', 'heart_overhead',
                                 'happy', 'shy', 'eat', 'stretch', 'sit', 'sleep']):
            button = QToolButton()
            button.setObjectName('pose')
            button.setCheckable(True)
            self.action_buttons[key] = button
            button.setText('看书 · 30 分钟' if key == 'read' else POSES[key][0])
            button.setIcon(QIcon(pet.sprites.thumbnail(key)))
            button.setIconSize(QSize(48, 52))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setMinimumSize(112, 78)
            button.clicked.connect(lambda checked=False, k=key: pet.perform_pose(k))
            grid.addWidget(button, i // 3, i % 3)
        add_page(actions, '陪伴')

        settings = QWidget()
        sl = QVBoxLayout(settings)
        sl.addWidget(QLabel('桌宠大小'))
        sizes = QHBoxLayout()
        self.size_group = QButtonGroup(self)
        self.size_buttons = {}
        for label, scale in [('小', .35), ('中', .55), ('大', .7)]:
            button = QPushButton(f'{label} · {round(340 * scale)}')
            button.setToolTip(f'角色画布高度 {round(340 * scale)} 逻辑像素')
            button.setCheckable(True)
            button.setChecked(pet.cur_h == round(340 * scale))
            button.clicked.connect(lambda checked=False, s=scale: pet.set_size(s))
            self.size_group.addButton(button)
            self.size_buttons[round(340 * scale)] = button
            sizes.addWidget(button)
        sl.addLayout(sizes)
        sl.addWidget(QLabel('动作节奏'))
        self.motion_rate = QComboBox()
        for label, rate in [('舒缓 · 0.75×（默认）', .75), ('自然 · 1×', 1.), ('轻快 · 1.5×', 1.5), ('活泼 · 2×', 2.)]:
            self.motion_rate.addItem(label, rate)
        self.motion_rate.setCurrentIndex(self.motion_rate.findData(pet.companion.data['motion_rate']))
        self.motion_rate.currentIndexChanged.connect(self.set_motion_rate)
        sl.addWidget(self.motion_rate)
        sl.addSpacing(12)
        sl.addWidget(QLabel('给她起个昵称'))
        self.nickname = QLineEdit(pet.companion.data['name'])
        self.nickname.setMaxLength(12)
        sl.addWidget(self.nickname)
        self.nickname.editingFinished.connect(self.save_name)
        self.water = QCheckBox('提醒我喝水、走动、放松眼睛')
        self.water.setChecked(pet.companion.data['reminders'])
        self.interval = QSpinBox()
        self.interval.setRange(1, 240)
        self.interval.setValue(pet.companion.data['reminder_minutes'])
        self.interval.setSuffix(' 分钟提醒一次')
        self.water.toggled.connect(self.save_reminder)
        self.interval.valueChanged.connect(self.save_reminder)
        sl.addWidget(self.water)
        sl.addWidget(self.interval)
        quiet = QCheckBox('免打扰：关闭随机说话和主动提醒')
        quiet.setChecked(pet.companion.data['quiet'])
        quiet.toggled.connect(self.set_quiet)
        sl.addWidget(quiet)
        guard = QCheckBox('全屏、游戏、会议、演示、锁屏时自动避让')
        guard.setChecked(pet.companion.data['game_guard'])
        guard.toggled.connect(self.set_game_guard)
        sl.addWidget(guard)
        sl.addStretch()
        add_page(settings, '设置')
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(1000)
        self.refresh()

    def refresh(self):
        state = self.pet.companion
        current_pose = state.current_pose()
        for key, button in self.action_buttons.items():
            button.setChecked(key == current_pose)
        for height, button in self.size_buttons.items():
            button.setChecked(height == self.pet.cur_h)

    def set_game_guard(self, on):
        self.pet.companion.data['game_guard'] = on
        self.pet.companion.save()

    def set_motion_rate(self, index):
        self.pet.companion.data['motion_rate'] = self.motion_rate.itemData(index)
        self.pet.companion.save()

    def start_focus(self):
        self.pet.start_reading()
        self.refresh()

    def save_reminder(self, *_):
        self.pet.companion.configure_reminder(self.water.isChecked(), self.interval.value())
        self.pet.companion.save()

    def save_name(self):
        self.pet.companion.data['name'] = self.nickname.text().strip() or '小伴'
        self.pet.setWindowTitle(self.pet.companion.data['name'] + ' · 动漫桌宠')
        self.pet.companion.save()
        self.refresh()

    def set_quiet(self, on):
        self.pet.companion.data['quiet'] = on
        self.pet.companion.save()

    def showEvent(self, event):
        self.refresh_timer.start(1000)
        self.pet.target = None
        self.refresh()
        super().showEvent(event)
        geo = (self.pet.screen() or QApplication.primaryScreen()).availableGeometry()
        self.resize(min(self.width(), geo.width() - 24), min(460, geo.height() - 40))
        self.move(max(geo.left(), min(self.pet.x() - self.width(), geo.right() - self.width())),
                  max(geo.top(), min(self.pet.y(), geo.bottom() - self.height())))

    def closeEvent(self, event):
        self.pet.chat_paused = False
        self.pet.companion.save()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.refresh_timer.stop()
        self.pet.chat_paused = False
        self.pet.companion.save()
        super().hideEvent(event)
