# -*- coding: utf-8 -*-
"""
小薛同学桌宠 —— 轻量动漫桌面陪伴 + 可选 AI 对话
左键单击：弹出功能列表（🗨️图标）→ 点击🗨️弹出聊天框
聊天时只禁用移动，呼吸/摇摆/小动作正常
"""
import ctypes
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
from companion import CompanionState, CompanionPanel, POSES, POSE_LINES
from animation import Animator, HEART_DURATION
from body_motion import BodyMotion, frame_interval
from game_guard import current_avoidance_reason
from desktop_geometry import clamp_position, dock_position, nearby_edge, movement_step, MotionPosition
from pet_theme import STYLE
from sprite_store import SpriteStore
from app_paths import settings_directory

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("配置读取失败:", e)
        return {
            "city": "汕头"
        }

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PySide6.QtGui import (QPainter, QPixmap, QFont, QColor, QIcon, QFontMetrics,
                           QPolygonF, QRegion, QPixmapCache)
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QSystemTrayIcon,
                               QMessageBox, QInputDialog, QLineEdit, QVBoxLayout,
                               QHBoxLayout, QPushButton, QFrame, QDialog, QToolButton, QLabel, QGridLayout)



# ===== DeepSeek 配置 =====
DS_BASE_URL = "https://api.deepseek.com/v1"
DS_MODEL = "deepseek-chat"
DS_SYSTEM = "你是温柔俏皮的动漫桌面陪伴角色，每句话尽量不超过25字，关心用户的日常，偶尔撒娇，不说粗话。你是虚拟角色，不声称自己是用户现实中的女朋友，也不编造她的真实经历或想法。"

if getattr(sys, "frozen", False):
    APP_DIR = str(settings_directory(os.path.dirname(sys.executable), frozen=True))
    BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    PYTHONW = sys.executable
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR
    PYTHONW = os.path.join(APP_DIR, ".venv", "Scripts", "pythonw.exe")
SPRITE_DIR = os.path.join(BUNDLE_DIR, "sprites-anime")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

BUBBLE_H = 76
MARGIN = 4
SIZE_LEVELS = {"小": 0.35, "中": 0.55, "大": 0.7}
SPEED = 380.0
TICK = 20

LINES = ["忙累了就休息一下呀～", "记得喝水，我在这里陪你。", "今天也要好好吃饭。", "想和你一起去看日落～", "慢慢来，你已经很努力啦。", "伸个懒腰，再继续吧！"]
REACT_LINES = ["嘿嘿，被你发现啦～", "戳我干嘛呀？", "好啦，陪你一会儿～", "今天有没有想我呀？"]
INNER_LINES = ["今天的晚霞会是什么颜色呢？", "想吃一点甜甜的东西～", "偷偷给你加个油。", "帽子有没有戴歪呀？"]
DRAG_LINES = ["哇——轻点轻点！", "起飞咯——", "放我下来！……好吧，再玩一次。", "要带我去哪里呀～"]
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                default,
                f,
                ensure_ascii=False,
                indent=4
            )
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


class ChatDialog(QDialog):
    """聊天对话框 - 缩小版，匹配你的样式"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 56)
        
        container = QFrame(self)
        container.setGeometry(0, 0, 420, 56)
        container.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 20px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(18, 0, 12, 0)
        layout.setSpacing(0)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("和动漫小伴聊聊天")
        self.input.setStyleSheet("""
            QLineEdit {
                color: #1a1a1a;
                font-size: 15px;
                font-family: Arial, "Microsoft YaHei", sans-serif;
                border: none;
                background: transparent;
            }
            QLineEdit:focus {
                border: none;
            }
        """)
        self.input.returnPressed.connect(self._on_submit)
        self.input.textChanged.connect(self._update_button_style)
        layout.addWidget(self.input)
        
        self.send_btn = QPushButton()
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setText("↑")
        self.send_btn.clicked.connect(self._on_submit)
        self.send_btn.setStyleSheet("""
            QPushButton {
                border-radius: 16px;
                background: #b9c7ff;
                border: none;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #a8b8f0;
            }
            QPushButton:pressed {
                background: #9aacd9;
            }
        """)
        layout.addWidget(self.send_btn)

    def _update_button_style(self):
        if self.input.text().strip():
            self.send_btn.setStyleSheet("""
                QPushButton {
                    border-radius: 16px;
                    background: #5686fe;
                    border: none;
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #4575ed;
                }
                QPushButton:pressed {
                    background: #3a66d9;
                }
            """)
        else:
            self.send_btn.setStyleSheet("""
                QPushButton {
                    border-radius: 16px;
                    background: #b9c7ff;
                    border: none;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #a8b8f0;
                }
                QPushButton:pressed {
                    background: #9aacd9;
                }
            """)

    def _on_submit(self):
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.accept()
            if self.parent():
                self.parent()._call_ds(text)
                self.parent().chat_paused = False

    def showEvent(self, event):
        self.input.setFocus()
        super().showEvent(event)

    def popup_at(self, x, y):
        self.move(int(x - self.width() / 2), int(y - self.height() - 10))
        self.show()
        self.raise_()

    def reject(self):
        if self.parent():
            self.parent().chat_paused = False
        super().reject()


class FunctionPanel(QFrame):
    """左键弹出的功能列表 - 白底矩形，只有一个🗨️图标"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.92);
                border-radius: 14px;
                border: 1px solid rgba(0,0,0,0.06);
            }
            QPushButton {
                background: transparent;
                border: none;
                font-size: 28px;
                padding: 10px 16px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(0,0,0,0.04);
            }
            QPushButton:pressed {
                background: rgba(0,0,0,0.08);
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)
        
        self.chat_btn = QPushButton("🗨️")
        self.chat_btn.setFixedSize(52, 48)
        self.chat_btn.clicked.connect(self._on_chat_clicked)
        layout.addWidget(self.chat_btn)
        companion_btn = QPushButton("♡")
        companion_btn.setToolTip("陪伴动作与设置")
        companion_btn.setFixedSize(52, 48)
        companion_btn.clicked.connect(self._on_companion_clicked)
        layout.addWidget(companion_btn)
        
        self.setFixedSize(68, 108)
        self.hide()

    def _on_companion_clicked(self):
        self.hide()
        self.parent().show_companion_panel()

    def hideEvent(self, event):
        if self.parent():
            self.parent().chat_paused = False
        super().hideEvent(event)
    
    def _on_chat_clicked(self):
        self.hide()
        if self.parent():
            self.parent()._show_chat_dialog()
    
    def popup_at(self, x, y):
        geo = (self.parent().screen() or QApplication.primaryScreen()).availableGeometry()
        self.move(max(geo.left(), min(int(x), geo.right() - self.width())),
                  max(geo.top(), min(int(y), geo.bottom() - self.height())))
        self.show()
        self.raise_()

class QuickPanel(QDialog):
    """Double-click shortcuts for real supported actions."""

    def __init__(self, pet):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.pet = pet
        self.setWindowTitle('快捷功能')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(342, 48)
        self.setStyleSheet("""
            QFrame#quickStrip {background:#faf8f4;border:0;border-radius:8px;}
            QPushButton {font-family:'Microsoft YaHei UI';font-size:12px;color:#304b5c;
                background:transparent;border:0;border-radius:7px;padding:0;}
            QPushButton:hover {background:#e0eaf0;}
            QPushButton:pressed {background:#cddfe9;}
            QPushButton:focus {border:1px solid #537c94;}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        surface = QFrame()
        surface.setObjectName('quickStrip')
        root.addWidget(surface)
        row = QHBoxLayout(surface)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(6)
        self.action_buttons = {}
        actions = [('happy', '摸头', '摸摸头', lambda: pet.perform_pose('happy')),
                   ('heart', '比心', '比个心', lambda: pet.perform_pose('heart')),
                   ('wave', '挥手', '挥挥手', lambda: pet.perform_pose('wave')),
                   ('eat', '蛋糕', '吃蛋糕', lambda: pet.perform_pose('eat')),
                   ('focus', '看书', '开始30分钟专注；重复点击不会重置计时', self.start_focus),
                   ('home', '小屋', '打开陪伴小屋', pet.show_companion_panel)]
        for key, name, tip, callback in actions:
            button = QPushButton(name)
            button.setFixedSize(50, 36)
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.clicked.connect(lambda checked=False, cb=callback: self.activate(cb))
            row.addWidget(button)
            self.action_buttons[key] = button

    def hideEvent(self, event):
        self.pet.chat_paused = False
        super().hideEvent(event)

    def activate(self, callback):
        self.hide()
        self.pet.chat_paused = False
        callback()

    def start_focus(self):
        self.pet.start_reading()

    def popup_at(self, x, y):
        screen = QApplication.screenAt(QPoint(round(x), round(y))) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        px, py = clamp_position(x - self.width() / 2, y - self.height() - 10,
                                self.width(), self.height(), geo)
        self.move(px, py)
        self.show()
        self.raise_()

class PetWindow(QWidget):
    def _set_city_dialog(self):
        city, ok = QInputDialog.getText(
            self,
            "设置城市",
            "输入城市名:",
            QLineEdit.EchoMode.Normal,
            self.cfg.get("city", "汕头")
        )

        print("输入框结果:", city, ok)

        if ok and city.strip():
            self.cfg["city"] = city.strip()
            print("cfg现在:", self.cfg["city"])
            self.say(f"城市已设置为{city}")

    def __init__(self):
        self.cfg = load_json(CONFIG_PATH, {
            "mode": "wander",
            "size": 0.55,
            "topmost": True,
            "passthrough": False,
            "autostart": False,
            "x": None,
            "y": None,
            "ds_api_key": "",
            "city": "汕头"
    })
        
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.cfg.get("topmost", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("小薛同学桌宠")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.companion = CompanionState(os.path.join(APP_DIR, "companion-state.json"))
        self.setWindowTitle(self.companion.data['name'] + ' · 动漫桌宠')
        self.companion_panel = None
        self.next_idle_pose = time.monotonic() + 25
        self.press_on_head = False
        self._double_click_handled = False
        self.game_hidden = False
        self._restore_after_game = False
        self._next_game_check = 0.
        self._game_events = []
        self._hit_regions = {}
        self._mask_region = QRegion()
        self._last_idle_pose = None
        
        if self.cfg.get('size') not in SIZE_LEVELS.values():
            self.cfg['size'] = .7 if isinstance(self.cfg.get('size'), (int, float)) and self.cfg['size'] > .7 else .55
            with open(CONFIG_PATH, 'w', encoding='utf-8') as stream:
                json.dump(self.cfg, stream, ensure_ascii=False, indent=2)
        self.sprites = SpriteStore(SPRITE_DIR, round(340 * self.cfg['size']))
        self.animator = Animator(SPRITE_DIR, [round(340 * self.cfg['size'])])
        self.icon = QIcon(self.sprites.thumbnail('正面'))
        self._hidden_since = None
        self._assets_asleep = False
        self._last_tick_time = time.monotonic()
        self._settle_until = 0.
        self._settle_facing = 1
        self.body_motion = BodyMotion()
        self.motion_position = MotionPosition()

        self.cur_h = round(340 * self.cfg["size"])
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(260, round(self.cur_h * 1.05), max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h)) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)

        # 状态
        self.mode = self.cfg["mode"] if self.cfg["mode"] in ("wander", "follow", "still", "dock") else "wander"
        self.dir = "down"
        self.facing = 1
        self.target = None
        self.rest_until = 0
        self.cur_speed = 0.0
        self.prev_key = None
        self.cross_t = 0.0
        self.action = None
        self.action_t = 0.0
        self.bubble_text = ""
        self.bubble_until = 0
        self.bubble_inner = False
        self.last_speak_tick = 0
        self.last_system_check = 0
        self.t = 0
        self.jump_t = 0
        self.dragging = False
        self.drag_offset = None
        self.drag_start_pos = None
        self.last_line = ""
        self.last_press_pos = None
        
        # AI 相关
        self.ds_busy = False
        self.chat_history = []  # 对话历史
        self.max_history = 40   # 最多记录40条
        self._say_queue = []    # 后台线程→主线程的气泡消息队列
        
        # 聊天暂停标志
        self.chat_paused = False
        
        # 功能列表
        self.function_panel = FunctionPanel(self)
        self.quick_panel = QuickPanel(self)
        # 单击延迟判定（等双击）：单击=回嘴+弹聊天面板，双击=快捷功能
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_single_click)
        
        # 聊天对话框
        self.chat_dialog = ChatDialog(self)
        self.chat_dialog.finished.connect(lambda _: setattr(self, 'chat_paused', False))
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK)

        self.bubble_font = QFont("Microsoft YaHei UI", 11)

        # 托盘
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("小薛同学桌宠")
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        x, y = self.cfg.get("x"), self.cfg.get("y")
        if x is None or y is None:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 80
            y = screen.bottom() - self.height() - 60
        self.move(int(x), int(y))
        if not (self.companion.data['game_guard'] and current_avoidance_reason(self.companion.data['avoidance_apps'])):
            self.show()
        else:
            self.game_hidden = True
            self._restore_after_game = True
        self.snap_into_screen()
        app = QApplication.instance()
        app.screenRemoved.connect(lambda _: QTimer.singleShot(0, self.snap_into_screen))
        if self.cfg.get("passthrough", False):
            self._apply_passthrough(True)

    # ---------- AI 方法 ----------
    def _call_ds(self, user_msg):
        if self.ds_busy:
            self.say("等等，上一句还没回完呢")
            return
        
        key = self.cfg.get("ds_api_key", "")
        if not key:
            self.say("请先在右键菜单里设置 DeepSeek Key！")
            return
        
        self.ds_busy = True
        
        # 构建消息列表
        messages = [{"role": "system", "content": DS_SYSTEM}]
        messages.extend(self.chat_history[-self.max_history:])
        messages.append({"role": "user", "content": user_msg})
        
        def worker():
            import requests
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": 100,
                "temperature": 0.9
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    reply = resp.json()["choices"][0]["message"]["content"].strip()
                    if len(reply) > 30:
                        reply = reply[:28] + "…"
                    # 存入历史
                    self.chat_history.append({"role": "user", "content": user_msg})
                    self.chat_history.append({"role": "assistant", "content": reply})
                    if len(self.chat_history) > self.max_history:
                        self.chat_history = self.chat_history[-self.max_history:]
                    self._queue_say(reply)
                else:
                    error_msg = resp.json().get("error", {}).get("message", str(resp.status_code))
                    self._queue_say(f"API错误: {error_msg[:12]}")
                    print(f"[DeepSeek] 状态码: {resp.status_code}, 返回: {resp.text}")
            except requests.exceptions.Timeout:
                self._queue_say("请求超时，检查网络")
            except requests.exceptions.ConnectionError:
                self._queue_say("连接失败，检查网络")
            except Exception as e:
                self._queue_say(f"请求失败: {str(e)[:12]}")
            finally:
                self.ds_busy = False
        
        threading.Thread(target=worker, daemon=True).start()

    # ---------- 绘制 ----------
    def paintEvent(self, _):
        self.restore_assets()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        now = self.t * TICK / 1000.0
        self._frame_hit_region = QRegion()

        if self.bubble_text and now < self.bubble_until:
            if self.bubble_inner:
                bfont = QFont(self.bubble_font)
                bfont.setItalic(True)
                bg, fg = QColor(232, 232, 238, 235), QColor(125, 125, 138)
            else:
                bfont = QFont(self.bubble_font)
                bg, fg = QColor(255, 255, 255, 235), QColor(60, 60, 80)
            fm = QFontMetrics(bfont)
            max_w = min(240, self.width() - 16)
            words = self.bubble_text
            lines = []
            cur = ""
            for ch in words:
                if fm.horizontalAdvance(cur + ch) > max_w - 20:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
            bw = max(fm.horizontalAdvance(l) for l in lines) + 20
            bh = len(lines) * fm.height() + 14
            bx = (self.width() - bw) / 2
            by = 6.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 10, 10)
            self._frame_hit_region |= QRegion(round(bx), round(by), round(bw), round(bh + 10))
            tail = QPointF(self.width() / 2, by + bh)
            p.drawPolygon(QPolygonF([tail, QPointF(tail.x() - 6, tail.y() + 8), QPointF(tail.x() + 6, tail.y() + 8)]))
            p.setPen(fg)
            p.setFont(bfont)
            for i, l in enumerate(lines):
                p.drawText(QRectF(bx, by + 7 + i * fm.height(), bw, fm.height()),
                           Qt.AlignmentFlag.AlignCenter, l)

        cx = self.width() / 2
        pose = self.companion.current_pose()
        walking = self.target is not None and not self.dragging and not pose

        def draw_one(key, opacity):
            if key is None:
                return
            name, h, facing = key
            self.animator.timeline.rate = self.companion.data['motion_rate']
            pix = self.animator.render(key, self.sprites, self.cur_speed)
            motion = self.body_motion.sample(now, walking=walking,
                phase=self.animator.timeline.phase if self.animator.timeline.action == 'walk' else None,
                speed=self.cur_speed, height=h, pose=pose, dragging=self.dragging,
                jump=self.jump_t, action=self.action, amount=self.action_t,
                tempo=self.companion.data['motion_rate'] / 1.5)
            ph = pix.height() * motion.scale_y
            pw = pix.width() * motion.scale_x
            dx = cx - pw / 2
            bottom = BUBBLE_H + MARGIN + self.cur_h
            dy = bottom - ph + motion.lift
            p.save()
            p.setOpacity(opacity)
            p.translate(*self.motion_position.offset(self.x(), self.y()))
            p.translate(cx, bottom)
            p.rotate(motion.rotation)
            p.translate(-cx, -bottom)
            p.drawPixmap(QRectF(dx, dy, pw, ph), pix, QRectF(0, 0, pix.width(), pix.height()))
            cache_key = pix.cacheKey()
            region = self._hit_regions.get(cache_key)
            if region is None:
                region = QRegion(pix.mask())
                if len(self._hit_regions) >= 64:
                    self._hit_regions.clear()
                self._hit_regions[cache_key] = region
            transform = p.worldTransform()
            transform.translate(dx, dy)
            transform.scale(pw / pix.width(), ph / pix.height())
            mapped = transform.map(region)
            self._frame_hit_region |= (mapped | mapped.translated(2, 0) | mapped.translated(-2, 0)
                                       | mapped.translated(0, 2) | mapped.translated(0, -2))
            p.restore()

        cur_key = self._sprite_key()
        draw_one(cur_key, 1.0)
        p.end()
        if self._frame_hit_region != self._mask_region and not self._frame_hit_region.isEmpty():
            self._mask_region = self._frame_hit_region
            if QApplication.platformName() != 'offscreen':
                self.setMask(self._mask_region)

    def _sprite_key(self):
        if self.dragging:
            return ('lift', self.cur_h, 1)
        pose = self.companion.current_pose()
        if pose:
            return (pose, self.cur_h, 1)
        if time.monotonic() < self._settle_until:
            return ('settle', self.cur_h, self._settle_facing)
        if self.target is not None and self.dir in ('left', 'right'):
            return ('walk1' if int(time.monotonic() * 5) % 2 == 0 else 'walk2', self.cur_h, self.facing)
        name = {"left": "侧面", "right": "侧面", "up": "背面", "down": "正面"}[self.dir]
        return (name, self.cur_h, self.facing if self.dir in ("left", "right") else 1)

    def _set_dir(self, d, facing=None):
        if d != self.dir:
            self.prev_key = self._sprite_key()
            self.cross_t = 1.0
            self.dir = d
        if facing is not None and facing != self.facing:
            self.facing = facing

    # ---------- 逻辑 ----------
    def tick(self):
        now_real = time.monotonic()
        elapsed = max(0., now_real - self._last_tick_time)
        self._last_tick_time = now_real
        dt = min(.1, elapsed)
        frame_factor = dt / (TICK / 1000.)
        self.t += elapsed / (TICK / 1000.)
        self.update_game_guard()
        hidden = self.game_hidden or not self.isVisible()
        if hidden:
            if self._hidden_since is None:
                self._hidden_since = now_real
            elif now_real - self._hidden_since >= 5:
                self.hibernate_assets()
        else:
            self._hidden_since = None
            self.restore_assets()
        pose = self.companion.current_pose()
        active = (self.target is not None or self.dragging or self.jump_t > 0 or self.action_t > 0
                  or self._settle_until > now_real or pose not in (None, 'sleep', 'read', 'sit')
                  or self.animator.timeline.blink_started is not None or self.body_motion.walk_weight > .01)
        interval = frame_interval(hidden=hidden, active=active, sleeping=self.companion.sleeping)
        timer_type = Qt.TimerType.CoarseTimer if hidden or self.companion.sleeping else Qt.TimerType.PreciseTimer
        if self.timer.timerType() != timer_type:
            self.timer.setTimerType(timer_type)
        if self.timer.interval() != interval:
            self.timer.setInterval(interval)
        if hidden:
            self._game_events.extend(self.companion.tick(suppress_reminders=True))
            return
        events = self.companion.tick() + self._game_events
        self._game_events = []
        if any(event in ('focus_done', 'break_done') for event in events):
            events = [event for event in events if event in ('focus_done', 'break_done')]
            self.companion.next_reminder = self.companion.clock() + self.companion.data['reminder_minutes'] * 60
        for event in events:
            text = self.reminder_text(event)
            if not self.companion.data['quiet']:
                self.say(text)
                if event in ('focus_done', 'break_done'):
                    self.tray.showMessage('陪伴提醒', text, QSystemTrayIcon.MessageIcon.Information, 5000)
            if event in ('water', 'walk', 'eyes'):
                self.companion.set_pose({'water':'drink', 'walk':'stretch', 'eyes':'sit'}[event], seconds=3.42 / self.companion.data['motion_rate'])
                self.animator.timeline.action = None

        if not self.isVisible():
            return

        # 处理后台线程（DeepSeek 等）排队的气泡消息，Qt 界面必须在主线程更新
        if self._say_queue:
            for text in self._say_queue:
                self.say(text)
            self._say_queue.clear()

        
        if self.jump_t > 0:
            self.jump_t = max(0.0, self.jump_t - 0.06 * frame_factor * self.companion.data['motion_rate'] / 1.5)
        if self.cross_t > 0:
            self.cross_t = max(0.0, self.cross_t - 0.15 * frame_factor)
        if self.action_t > 0:
            self.action_t = max(0.0, self.action_t - 0.03 * frame_factor * self.companion.data['motion_rate'] / 1.5)
            if self.action_t == 0:
                self.action = None
        
        if (self.companion.current_pose() or
                (self.companion_panel is not None and self.companion_panel.isVisible()) or
                self.quick_panel.isVisible() or self.function_panel.isVisible() or self.chat_dialog.isVisible()):
            self.target = None
            self.cur_speed = 0
            self.update()
            return

        if self.chat_paused:
            self.update()
            return
        
        if self.dragging:
            self.update()
            return
        now_ms = self.t * TICK

        if self.mode == "follow":
            cursor = self.cursor().pos()
            screen = QApplication.screenAt(cursor) or self.screen() or QApplication.primaryScreen()
            geo = screen.availableGeometry()
            near = (self.x() - 100 <= cursor.x() <= self.x() + self.width() + 100 and
                    self.y() - 100 <= cursor.y() <= self.y() + self.height() + 100)
            if near:
                self.target = None
            else:
                tx = max(geo.left(), min(geo.right() - self.width(), cursor.x() - self.width() / 2))
                ty = max(geo.top(), min(geo.bottom() - self.height(), cursor.y() - 90))
                self.target = (tx, ty)
        elif self.mode == "dock":
            self.snap_into_screen()
            self._maybe_idle_action()
            self.update()
            return
        elif self.mode == "wander":
            if self.target is None:
                if now_ms < self.rest_until:
                    self._maybe_idle_action()
                    self.update()
                    return
                geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
                self.target = (random.randint(geo.left(), max(geo.left(), geo.right() - self.width())),
                               random.randint(geo.top(), max(geo.top(), geo.bottom() - self.height())))
        else:
            self._maybe_idle_action()
            self.update()
            return

        if self.target is not None:
            cx, cy = self.motion_position.origin(self.x(), self.y())
            dx, dy = self.target[0] - cx, self.target[1] - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 2:
                if self.dir in ('left', 'right'):
                    self._settle_until = time.monotonic() + .18
                    self._settle_facing = self.facing
                self.move(*self.motion_position.commit(*self.target))
                self.target = None
                self.cur_speed = 0.
                self.rest_until = self.t * TICK + random.randint(8000, 18000)
                self._set_dir("down")
            else:
                step, self.cur_speed = movement_step(dist, self.cur_speed,
                    SPEED * self.companion.data['motion_rate'] / 1.5, dt)
                nx, ny = cx + dx / dist * step, cy + dy / dist * step
                self.move(*self.motion_position.commit(nx, ny))
                if abs(dx) > abs(dy) * 1.15:
                    self._set_dir("left" if dx < 0 else "right", 1 if dx < 0 else -1)
                elif abs(dy) > abs(dx) * 1.15:
                    self._set_dir("up" if dy < 0 else "down")
            if random.random() < 0.002 and self.jump_t == 0:
                self.jump_t = 0.5
        self.update()

    def _maybe_idle_action(self):
        if self.companion.data['quiet']:
            return
        if time.monotonic() >= self.next_idle_pose:
            choices = [key for key in ('wave', 'sit', 'stretch', 'shy') if key != self._last_idle_pose]
            key = random.choice(choices)
            self._last_idle_pose = key
            self.companion.set_pose(key, seconds=(3.08 if key == 'wave' else 3) / self.companion.data['motion_rate'])
            self.next_idle_pose = time.monotonic() + random.randint(25, 55)
        if random.random() < 0.01:
            pick = random.random()
            if pick < 0.35:
                self.jump_t = 1.0
            elif pick < 0.6:
                self.action, self.action_t = "sway", 1.0
            elif pick < 0.8:
                self.action, self.action_t = "stretch", 1.0
            elif pick < 0.9:
                if self.t - self.last_speak_tick >= 1500:
                    self.last_speak_tick = self.t
                    if pick < 0.82:
                        self.say(random.choice(INNER_LINES), inner=True)
                    else:
                        self.say(random.choice(LINES))

    def _queue_say(self, text):
        """后台线程调用：只入队，由主线程 tick 统一弹出显示（线程安全）"""
        self._say_queue.append(text)

    def say(self, text, inner=False):
        if text == self.last_line and not text.startswith("天气"):
            return
        self.last_line = text
        self.bubble_inner = inner
        self.bubble_text = f"（{text}）" if inner else text
        self.bubble_until = self.t * TICK / 1000.0 + 2.8
        self.update()

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.press_on_head = BUBBLE_H <= e.position().y() <= BUBBLE_H + self.cur_h * 0.48
            self.last_press_pos = e.globalPosition().toPoint()
            self.dragging = False
            self.drag_start_pos = e.globalPosition().toPoint()
            self.function_panel.hide()
            self.chat_dialog.hide()
            self.chat_paused = True

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos is not None:
            delta = e.globalPosition().toPoint() - self.drag_start_pos
            if not self.dragging and delta.manhattanLength() > 6:
                self.dragging = True
                self.drag_offset = e.globalPosition().toPoint() - QPoint(self.x(), self.y())
            if self.dragging and self.drag_offset is not None:
                pos = e.globalPosition().toPoint() - self.drag_offset
                self.move(pos)
                if abs(delta.x()) > 10:
                    self._set_dir("left" if delta.x() < 0 else "right", 1 if delta.x() < 0 else -1)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._double_click_handled:
                self._double_click_handled = False
                self.chat_paused = False
                self.drag_start_pos = None
                self.last_press_pos = None
                return
            if self.dragging:
                self.dragging = False
                self.drag_offset = None
                self.drag_start_pos = None
                self._set_dir("down", 1)
                self.target = None
                self.rest_until = self.t * TICK + random.randint(6000, 14000)
                if random.random() < 0.5:
                    self.say(random.choice(DRAG_LINES))
                self.chat_paused = False
                screen = QApplication.screenAt(e.globalPosition().toPoint()) or self.screen() or QApplication.primaryScreen()
                if self.mode == 'dock':
                    self.set_mode('still')
                self.snap_into_screen(screen)
                edge = nearby_edge(self.x(), self.y(), self.width(), self.height(), screen.availableGeometry())
                if edge:
                    self.dock_to(edge, screen)
                self.companion.set_pose('shy', seconds=3)
            else:
                self.chat_paused = False
                self._click_timer.start(280)  # 等双击判定；单击则回嘴+弹聊天面板
            self.last_press_pos = None
            self.drag_start_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._double_click_handled = True
            self._click_timer.stop()
            self.quick_panel.popup_at(self.x() + self.width() / 2, self.y() + BUBBLE_H)

    def _on_single_click(self):
        """单击互动并打开功能入口，点击角色之外收起。"""
        if self.press_on_head:
            self.perform_pose('happy')
            return
        if random.random() < 0.7:
            self.jump_t = 1.0
        if random.random() < 0.6:
            self.say(random.choice(REACT_LINES))
        panel = self.function_panel
        panel.popup_at(self.x() + self.width() / 2 - panel.width() / 2,
                       self.y() - panel.height() - 10)

    def _show_chat_dialog(self):
        key = self.cfg.get("ds_api_key", "")
        if not key:
            self.say("请先在右键菜单里设置 DeepSeek Key！")
            self.chat_paused = False
            return
        self.chat_paused = True
        self.chat_dialog.popup_at(
            self.x() + self.width() / 2,
            self.y() + BUBBLE_H
        )

    """def _get_city_by_ip(self):
        try:
            r = requests.get("http://ip-api.com/json/?fields=city&lang=zh-CN", timeout=5)
            if r.status_code == 200:
                city = r.json().get("city", "")
                if city:
                    return city
        except:
            pass
        return "汕头" """

    def _get_weather(self):
        import requests
        try:
            city = self.cfg.get("city", "汕头")
            print("当前城市:", city)

            url = f"https://wttr.in/{city}?format=j1"

            r = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            print("状态:", r.status_code)
            print(r.text[:500])

            data = r.json()

            weather = data["current_condition"][0]

            temp = weather["temp_C"]

            weather_map = {
                "Sunny": "晴",
                "Clear": "晴",
                "Partly cloudy": "多云",
                "Cloudy": "阴",
                "Light rain": "小雨",
                "Moderate rain": "中雨",
                "Heavy rain": "大雨"
            }

            raw_weather = weather["weatherDesc"][0]["value"]

            desc = weather_map.get(raw_weather, raw_weather)

            self._queue_say(f"{city}今天{temp}°，天气{desc}")

        except Exception as e:
            print("天气错误:", repr(e))
            self._queue_say("天气获取失败")
    

    def _build_menu(self):
        m = QMenu(self)
        m.addAction('陪伴小屋', self.show_companion_panel)
        actions = m.addMenu('互动动作')
        for key in ['wave', 'heart', 'heart_finger', 'heart_chest', 'heart_overhead', 'drink', 'shy', 'happy', 'read', 'sit', 'sleep', 'eat', 'stretch']:
            action = actions.addAction(POSES[key][0])
            action.triggered.connect(lambda checked=False, k=key: self.perform_pose(k))
        m.addAction('起床 / 自由活动', self.wake_companion)
        m.addSeparator()
        mode_menu = m.addMenu("模式")
        for label, key in [("自由散步", "wander"), ("跟随鼠标", "follow"), ("原地待着", "still"), ('边缘停靠', 'dock')]:
            a = mode_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.mode == key)
            a.triggered.connect(lambda _, k=key: self.set_mode(k))
        size_menu = m.addMenu("大小")
        for label, mult in SIZE_LEVELS.items():
            a = size_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(abs(self.cur_h - 340 * mult) < 2)
            a.triggered.connect(lambda _, v=mult: self.set_size(v))
        dock_menu = m.addMenu('停靠屏幕边缘')
        for label, edge in [('左边', 'left'), ('右边', 'right'), ('上边', 'top'), ('底部', 'bottom')]:
            a = dock_menu.addAction(label)
            a.triggered.connect(lambda checked=False, e=edge: self.dock_to(e))
        screens = m.addMenu('移到显示器')
        for i, screen in enumerate(QApplication.screens()):
            a = screens.addAction(f'{i + 1} · {screen.name()}')
            a.triggered.connect(lambda checked=False, s=screen: self.move_to_screen(s))
        m.addAction("设置 Key", self._set_key_dialog)
        m.addAction("查看天气", lambda: threading.Thread(target=self._get_weather, daemon=True).start())
        m.addAction("设置城市", self._set_city_dialog)
        m.addSeparator()
        m.addAction("显示/隐藏", self.toggle_visible)
        m.addAction("回到屏幕内", self.snap_into_screen)
        pa = m.addAction("鼠标穿透（点不到它）")
        pa.setCheckable(True)
        pa.setChecked(self.cfg["passthrough"])
        pa.triggered.connect(lambda on: self.set_passthrough(on))
        ta = m.addAction("窗口置顶")
        ta.setCheckable(True)
        ta.setChecked(self.cfg["topmost"])
        ta.triggered.connect(lambda on: self.set_topmost(on))
        aa = m.addAction("开机自启")
        aa.setCheckable(True)
        aa.setChecked(self.cfg["autostart"])
        aa.triggered.connect(lambda on: self.set_autostart(on))
        m.addSeparator()
        m.addAction("退出", self.quit_app)
        return m

    def _set_key_dialog(self):
        key, ok = QInputDialog.getText(
            self, 
            "设置 DeepSeek Key", 
            "输入你的 API Key（从 platform.deepseek.com 获取）:",
            QLineEdit.EchoMode.Normal,
            self.cfg.get("ds_api_key", "")
        )
        if ok and key.strip():
            self.cfg["ds_api_key"] = key.strip()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
            self.say("Key 设置成功！")
        elif ok and not key.strip():
            self.say("Key 不能为空")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            old_menu = self.tray.contextMenu()
            self.tray.setContextMenu(self._build_menu())
            if old_menu is not None:
                old_menu.deleteLater()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def contextMenuEvent(self, e):
        menu = self._build_menu()
        try:
            menu.exec(e.globalPos())
        finally:
            menu.deleteLater()

    # ---------- 功能 ----------
    def hibernate_assets(self):
        if self._assets_asleep:
            return
        self.animator.release()
        self.sprites.release()
        self._hit_regions.clear()
        self.prev_key = None
        QPixmapCache.clear()
        self._assets_asleep = True

    def restore_assets(self):
        if not self._assets_asleep:
            return
        self.sprites.ensure(self.cur_h)
        self.animator.ensure_height(self.cur_h)
        self._assets_asleep = False

    def update_game_guard(self):
        now = time.monotonic()
        if now < self._next_game_check:
            return
        self._next_game_check = now + .4
        enabled = self.companion.data['game_guard']
        reason = current_avoidance_reason(self.companion.data['avoidance_apps']) if enabled else ''
        if reason:
            self._avoidance_until = now + 1.2
        active = enabled and (bool(reason) or now < getattr(self, '_avoidance_until', 0))
        if active and not self.game_hidden:
            self._restore_after_game = self.isVisible()
            self.game_hidden = True
            self.animator.clear_transient()
            self._hit_regions.clear()
            self.hide()
            for panel in (self.function_panel, self.quick_panel, self.chat_dialog, self.companion_panel):
                if panel is not None:
                    panel.hide()
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, QMenu):
                    widget.close()
            self.target = None
            self.chat_paused = False
            self._click_timer.stop()
        elif not active and self.game_hidden:
            self.game_hidden = False
            if self._restore_after_game:
                self.show()
            self._restore_after_game = False

    def show_companion_panel(self):
        if self.companion.data['game_guard'] and current_avoidance_reason(self.companion.data['avoidance_apps']):
            return
        self.chat_paused = False
        self.function_panel.hide()
        if self.companion_panel is None:
            self.companion_panel = CompanionPanel(self)
        self.companion_panel.show()
        self.companion_panel.raise_()
        self.companion_panel.activateWindow()

    def reminder_text(self, kind):
        from companion_lines import REMINDERS
        choices = REMINDERS.get(kind, REMINDERS['water'])
        previous = getattr(self, '_last_reminder_lines', {})
        text = random.choice([line for line in choices if line != previous.get(kind)] or choices)
        previous[kind] = text
        self._last_reminder_lines = previous
        return text

    def start_reading(self):
        self.target = None
        if self.companion.phase == 'focus':
            self.say(f'还剩 {math.ceil(self.companion.remaining() / 60)} 分钟，我陪你慢慢来。')
        else:
            self.companion.start_focus(30)
            self.say(self.reminder_text('reading'))
        self.update()
        if self.companion_panel is not None:
            self.companion_panel.refresh()

    def perform_pose(self, key):
        if key in ('heart_finger', 'heart_chest', 'heart_overhead') and self.companion.current_pose() == key:
            return
        if key == 'read':
            self.start_reading()
            return
        if key == 'heart':
            variants = ('heart_finger', 'heart_chest', 'heart_overhead')
            index = getattr(self, '_heart_variant', 0)
            key = variants[index % len(variants)]
            self._heart_variant = index + 1
        self.target = None
        self.cross_t = 0
        if key in ('wave', 'heart_finger', 'heart_chest', 'heart_overhead', 'drink'):
            self.animator.timeline.action = None
        durations = {'wave': 3.08, 'happy': 2.4, 'heart': 3.6, 'shy': 3.,
                     'stretch': 3., 'eat': 4.5, 'sit': 10., 'read': 12.,
                     'heart_finger':HEART_DURATION, 'heart_chest':HEART_DURATION, 'heart_overhead':HEART_DURATION, 'drink':3.42}
        self.companion.set_pose(key, seconds=durations.get(key, 4.5) / self.companion.data['motion_rate'])
        self.say(POSE_LINES.get(key, '我在这里呀～'))
        self.companion.save()
        self.update()

    def wake_companion(self):
        self.companion.wake()
        self.companion.cancel_focus()
        self.chat_paused = False
        self.cross_t = 0
        self.say('休息好啦，我们继续吧～')

    def set_mode(self, mode):
        self.mode = mode
        self.target = None
        self.cfg["mode"] = mode
        self.cur_speed = 0.
        if mode == 'dock':
            self.snap_into_screen()
        self.save_position()

    def set_size(self, mult):
        if mult not in SIZE_LEVELS.values():
            mult = .7 if isinstance(mult, (int, float)) and mult > .7 else .55
        self.cur_h = round(340 * mult)
        self.sprites.ensure(self.cur_h)
        self.animator.ensure_height(self.cur_h)
        self._assets_asleep = False
        self._hit_regions.clear()
        self.cfg["size"] = mult
        self.cross_t = 0.0
        self.prev_key = None
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(260, round(self.cur_h * 1.05), max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h)) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)
        self.snap_into_screen()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as stream:
            json.dump(self.cfg, stream, ensure_ascii=False, indent=2)

    def dock_to(self, edge, screen=None):
        self.companion.wake()
        self.set_mode('dock')
        self.cfg['dock_edge'] = edge
        self.snap_into_screen(screen)
        self.say('我在边上陪你，不挡着你～')
        self.save_position()

    def move_to_screen(self, screen):
        if screen not in QApplication.screens():
            return
        geo = screen.availableGeometry()
        self.target = None
        self.move(geo.center().x() - self.width() // 2, geo.bottom() - self.height() - 16)
        self.snap_into_screen(screen)
        self.save_position()

    def save_position(self):
        self.cfg['x'], self.cfg['y'] = self.x(), self.y()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as stream:
            json.dump(self.cfg, stream, ensure_ascii=False, indent=2)

    def snap_into_screen(self, screen=None):
        screen = screen if screen in QApplication.screens() else self.screen() or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        if self.mode == 'dock':
            x, y = dock_position(self.x(), self.y(), self.width(), self.height(), geo, self.cfg.get('dock_edge', 'bottom'))
        else:
            x, y = clamp_position(self.x(), self.y(), self.width(), self.height(), geo)
        self.move(x, y)

    def _apply_passthrough(self, on):
        hwnd = int(self.winId())
        GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_LAYERED
        if on:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)

    def set_passthrough(self, on):
        self.cfg["passthrough"] = bool(on)
        self._apply_passthrough(bool(on))
        if on:
            self.say("我隐身了！右键托盘图标解除～")

    def set_topmost(self, on):
        self.cfg["topmost"] = bool(on)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(on))
        self.show()

    def set_autostart(self, on):
        self.cfg["autostart"] = bool(on)
        lnk = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup", "XiaoxuePet.lnk")
        try:
            if on:
                arguments = '' if getattr(sys, 'frozen', False) else '"'+os.path.join(APP_DIR, '桌宠.py')+'"'
                working = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else APP_DIR
                ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{}');"
                      "$s.TargetPath='{}';$s.Arguments='{}';$s.WorkingDirectory='{}';$s.Save()"
                      .format(*(value.replace("'", "''") for value in (lnk, PYTHONW, arguments, working))))
                subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
                self.say("已开机自启，明天见～")
            else:
                if os.path.exists(lnk):
                    os.remove(lnk)
                self.say("已取消开机自启")
        except Exception as ex:
            QMessageBox.warning(self, "开机自启", f"设置失败：{ex}")

    def toggle_visible(self):
        if self.game_hidden:
            return
        if self.isVisible():
            self.hide()
            for panel in (self.function_panel, self.quick_panel, self.chat_dialog, self.companion_panel):
                if panel is not None:
                    panel.hide()
            self.chat_paused = False
            self.animator.clear_transient()
            self._hit_regions.clear()
        else:
            self.show()
            self.raise_()

    def quit_app(self):
        self.companion.save()
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        self.tray.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = PetWindow()
    if '--smoke-test' in sys.argv:
        # Packaging smoke test stays offline and exits itself without persisting UI state.
        w.timer.stop()
        w.hide()
        for name in ('正面', 'walk1', 'wave', 'heart_finger', 'heart_chest', 'heart_overhead', 'drink', 'read', 'sleep'):
            for height in (119, 187, 238):
                w.sprites.ensure(height)
                if w.animator.render((name, height, 1), w.sprites, 0).isNull():
                    raise RuntimeError('Missing packaged sprite: '+name)
        w.tray.hide()
        QTimer.singleShot(0, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "小薛同学桌宠出错", str(ex))
        except Exception:
            pass
        raise
