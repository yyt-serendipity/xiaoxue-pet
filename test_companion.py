import importlib.util
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from companion import CompanionState, POSES


class Clock:
    now = 1000.
    def __call__(self):
        return self.now


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.state = CompanionState(Path(self.temp.name) / 'state.json', self.clock)

    def tearDown(self):
        self.temp.cleanup()

    def test_focus_pause_resume_and_complete_once(self):
        s = self.state
        s.start_focus(1)
        self.clock.now += 20
        s.pause_focus()
        self.clock.now += 120
        self.assertEqual(s.remaining(), 40)
        self.assertEqual(s.tick(), [])
        s.pause_focus()
        self.clock.now += 40
        self.assertEqual(s.tick(), ['focus_done'])
        self.assertEqual(s.tick(), [])
        self.assertEqual(s.data['sessions'], 1)
        self.assertEqual(s.data['focus_minutes'], 1)

    def test_cancel_and_sleep_do_not_count_completion(self):
        s = self.state
        s.start_focus(1)
        s.set_pose('sleep')
        self.clock.now += 120
        self.assertEqual(s.tick(), [])
        self.assertEqual(s.current_pose(), 'sleep')
        self.assertEqual(s.data['sessions'], 0)
        self.assertGreater(s.data['energy'], 85)
        s.wake()
        self.assertIsNone(s.current_pose())

    def test_reminders_deferred_without_backlog(self):
        s = self.state
        s.configure_reminder(True, 1)
        s.data['quiet'] = True
        self.clock.now += 3600
        self.assertEqual(s.tick(), [])
        s.data['quiet'] = False
        self.assertEqual(s.tick(), ['water'])
        self.assertEqual(s.tick(), [])
        s.configure_reminder(False, 1)
        self.clock.now += 120
        self.assertEqual(s.tick(), [])

    def test_reminder_categories_rotate_and_focus_defers(self):
        s = self.state
        s.configure_reminder(True, 1)
        for expected in ('water', 'walk', 'eyes', 'water'):
            self.clock.now += 61
            self.assertEqual(s.tick(), [expected])
        s.start_focus(30)
        self.clock.now += 61
        self.assertEqual(s.tick(), [])
        self.clock.now += 1800
        self.assertEqual(s.tick(), ['focus_done'])

    def test_persistence_does_not_resume_old_timer_or_decay_offline(self):
        s = self.state
        s.data['name'] = '测试昵称'
        s.data['fullness'] = 65.
        s.start_focus(25)
        self.assertTrue(s.save())
        self.clock.now += 86400
        restored = CompanionState(s.path, self.clock)
        self.assertEqual(restored.data['name'], '测试昵称')
        self.assertEqual(restored.data['fullness'], 65.)
        self.assertIsNone(restored.phase)

    def test_corrupt_save_and_reward_limits(self):
        s = self.state
        s.path.write_text('broken', encoding='utf-8')
        restored = CompanionState(s.path, self.clock)
        self.assertEqual(restored.data['name'], '小薛同学')
        for _ in range(20):
            restored.set_pose('eat')
        self.assertEqual(restored.data['fullness'], 95.)
        self.clock.now += 11
        restored.set_pose('eat')
        self.assertEqual(restored.data['fullness'], 100.)

    def test_break_does_not_count_as_focus(self):
        self.state.start_focus(1, 'break')
        self.clock.now += 60
        self.assertEqual(self.state.tick(), ['break_done'])
        self.assertEqual(self.state.data['sessions'], 0)


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
        cls.app.setFont(QFont('Microsoft YaHei', 10))
        root = Path(__file__).parent
        spec = importlib.util.spec_from_file_location('pet_app', root / '桌宠.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.module.current_avoidance_reason = lambda *args: False
        cls.root = root

    def test_actions_panel_render_and_timer_integration(self):
        with tempfile.TemporaryDirectory() as temporary:
            m = self.module
            old_dir, old_config = m.APP_DIR, m.CONFIG_PATH
            m.APP_DIR, m.CONFIG_PATH = temporary, str(Path(temporary) / 'config.json')
            pet = m.PetWindow()
            pet.timer.stop()
            pet.check_system_status = lambda: None
            try:
                self.assertEqual(pet.companion.data['motion_rate'], .75)
                self.assertNotIn('特大', m.SIZE_LEVELS)
                pet.set_size(.9)
                self.assertEqual(pet.cur_h, 238)
                self.assertEqual(len(pet.sprites), 15)
                for scale in m.SIZE_LEVELS.values():
                    pet.set_size(scale)
                    self.assertEqual({height for _, height in pet.sprites}, {pet.cur_h})
                    self.assertEqual(pet.animator.loaded_height, pet.cur_h)
                    for bank in pet.animator.frames.values():
                        self.assertEqual(list(bank), [pet.cur_h])
                    for name in POSES:
                        pet.companion.set_pose(name)
                        pet.cross_t = 0
                        self.assertEqual(pet._sprite_key()[0], name)
                        pet.repaint()
                        self.app.processEvents()
                        self.assertFalse(pet.sprites[(name, pet.cur_h)].isNull())
                        self.assertFalse(pet._mask_region.isEmpty())
                        self.assertFalse(pet._mask_region.contains(QPoint(0, pet.height() - 1)))
                pet.set_size(.7)
                pet.dock_to('right')
                self.assertEqual(pet.mode, 'dock')
                geo = pet.screen().availableGeometry()
                self.assertEqual(pet.x(), geo.right() + 1 - pet.width() - 8)
                pet.set_size(.35)
                self.assertEqual(pet.x(), geo.right() + 1 - pet.width() - 8)
                pet.set_mode('still')
                pet.set_size(.7)
                pet.wake_companion()
                pet.target, pet.dir = (pet.x() + 100, pet.y()), 'left'
                self.assertIn(pet._sprite_key()[0], ('walk1', 'walk2'))
                pet.dragging = True
                self.assertEqual(pet._sprite_key()[0], 'lift')
                pet.dragging = False
                for variant in ('heart_finger', 'heart_chest', 'heart_overhead'):
                    pet.perform_pose('heart')
                    self.assertEqual(pet.companion.current_pose(), variant)
                    pose_deadline = pet.companion.pose_until
                    pet.perform_pose(variant)
                    self.assertEqual(pet.companion.pose_until, pose_deadline)
                    pet.animator.render((variant, pet.cur_h, 1), pet.sprites, 0)
                    self.assertEqual(sum(key.startswith('heart_') for key in pet.animator.frames), 1)
                pet.show_companion_panel()
                self.app.processEvents()
                panel = pet.companion_panel
                panel.action_buttons['read'].click()
                self.assertEqual(pet.companion.focus_duration, 30)
                original_deadline = pet.companion.deadline
                panel.action_buttons['read'].click()
                self.assertEqual(pet.companion.deadline, original_deadline)
                pet.tick()
                self.assertIsNone(pet.target)
                self.assertEqual(pet._sprite_key()[0], 'read')
                pet.companion.deadline = pet.companion.clock() - 1
                pet.companion.data['quiet'] = True
                pet.tick()
                self.assertEqual(pet.companion.data['sessions'], 1)
                panel.refresh()
                panel.grab().save(str(self.root / 'sprites-anime' / 'panel-preview.png'))
                for index, name in [(1, 'settings')]:
                    panel.tabs.setCurrentIndex(index)
                    self.app.processEvents()
                    panel.grab().save(str(self.root / 'sprites-anime' / f'panel-{name}.png'))
                self.assertEqual(panel.tabs.count(), 2)
                self.assertEqual(panel.tabs.tabText(0), '陪伴')
                self.assertFalse(hasattr(panel, 'heart_game'))
                panel.motion_rate.setCurrentIndex(panel.motion_rate.findData(2.))
                self.assertEqual(pet.companion.data['motion_rate'], 2.)
                panel.motion_rate.setCurrentIndex(panel.motion_rate.findData(.75))
                self.assertEqual(pet.companion.data['motion_rate'], .75)
                panel.close()
                self.assertFalse(panel.refresh_timer.isActive())
                # Game guard hides everything and preserves manual hidden state.
                pet.show()
                m.current_avoidance_reason = lambda *args: True
                pet._next_game_check = 0
                pet.update_game_guard()
                self.assertTrue(pet.game_hidden)
                self.assertFalse(pet.isVisible())
                pet.tick()
                self.assertEqual(pet.timer.interval(), 1000)
                m.current_avoidance_reason = lambda *args: False
                pet._next_game_check = 0
                pet._avoidance_until = 0
                pet.update_game_guard()
                self.assertTrue(pet.isVisible())
                pet.tick()
                self.assertEqual(pet.timer.interval(), m.TICK)
                pet.hide()
                m.current_avoidance_reason = lambda *args: True
                pet._next_game_check = 0
                pet.update_game_guard()
                m.current_avoidance_reason = lambda *args: False
                pet._next_game_check = 0
                pet._avoidance_until = 0
                pet.update_game_guard()
                self.assertFalse(pet.isVisible())
                pet.show()
                panel.close()
                QTest.mouseDClick(pet, Qt.MouseButton.LeftButton)
                QTest.mouseRelease(pet, Qt.MouseButton.LeftButton)
                self.assertTrue(pet.quick_panel.isVisible())
                self.app.processEvents()
                pet.quick_panel.grab().save(str(self.root / 'sprites-anime' / 'quick-preview.png'))
                self.assertFalse(pet._click_timer.isActive())
                pet.tick()
                self.assertIsNone(pet.target)
                self.assertEqual(set(pet.quick_panel.action_buttons), {'happy', 'heart', 'wave', 'eat', 'focus', 'home'})
                pet.quick_panel.action_buttons['eat'].click()
                self.assertFalse(pet.quick_panel.isVisible())
                self.assertFalse(pet.chat_paused)
                self.assertEqual(pet._sprite_key()[0], 'eat')
                pet.companion.cancel_focus()
                pet.quick_panel.action_buttons['focus'].click()
                self.assertEqual(pet.companion.phase, 'focus')
                self.assertEqual(pet.companion.focus_duration, 30)
                deadline = pet.companion.deadline
                pet.quick_panel.action_buttons['focus'].click()
                self.assertEqual(pet.companion.deadline, deadline)
                pet.show_companion_panel()
                pet.companion_panel.tabs.setCurrentIndex(0)
                self.assertFalse(hasattr(pet.companion_panel, 'bars'))
                self.assertTrue(pet.companion_panel.windowFlags() & Qt.WindowType.FramelessWindowHint)
                QTest.keyClick(pet.companion_panel, Qt.Key.Key_Escape)
                self.assertFalse(pet.companion_panel.isVisible())
                self.assertFalse(pet.companion_panel.refresh_timer.isActive())
                pet.quick_panel.popup_at(pet.x(), pet.y())
                pet.chat_paused = True
                QTest.keyClick(pet.quick_panel, Qt.Key.Key_Escape)
                self.assertFalse(pet.quick_panel.isVisible())
                self.assertFalse(pet.chat_paused)
                for i in range(100):
                    pet.animator.render(('read', pet.cur_h, 1), pet.sprites, 0)
                self.assertLessEqual(pet.animator.cache_bytes, pet.animator.cache_budget)
                a = pet.animator.render(('read', pet.cur_h, 1), pet.sprites, 0)
                pet.animator.transition_started -= 1
                a = pet.animator.render(('read', pet.cur_h, 1), pet.sprites, 0)
                b = pet.animator.render(('read', pet.cur_h, 1), pet.sprites, 0)
                self.assertEqual(a.cacheKey(), b.cacheKey())
                pet.animator.clear_transient()
                self.assertEqual(pet.animator.cache_bytes, 0)
                self.assertEqual(len(pet.animator.cache), 0)
                self.assertFalse(pet.animator.render(('read', pet.cur_h, 1), pet.sprites, 0).isNull())
                pet.hibernate_assets()
                self.assertEqual(len(pet.sprites), 0)
                self.assertEqual(pet.animator.frames, {})
                pet.restore_assets()
                self.assertEqual(len(pet.sprites), 15)
                self.assertEqual(pet.animator.loaded_height, pet.cur_h)
                pet.hide()
                pet._hidden_since = m.time.monotonic() - 6
                pet.tick()
                self.assertTrue(pet._assets_asleep)
                self.assertEqual(len(pet.sprites), 0)
                pet.show()
                pet.tick()
                self.assertFalse(pet._assets_asleep)
                pet.companion.wake()
                pet.companion.cancel_focus()
                pet.target = None
                pet.jump_t = pet.action_t = 0
                pet._settle_until = 0
                pet.animator.timeline.blink_started = None
                pet.set_mode('still')
                pet.tick()
                self.assertEqual(pet.timer.interval(), 33)
                pet.companion.set_pose('sleep')
                pet.tick()
                self.assertEqual(pet.timer.interval(), 100)
                pet.companion.set_pose('wave')
                pet.tick()
                self.assertEqual(pet.timer.interval(), m.TICK)
                # Review every runtime frame against a light background with labels.
                canvas = QImage(1040, 1410, QImage.Format.Format_ARGB32)
                canvas.fill(QColor('#faf8f5'))
                painter = QPainter(canvas)
                painter.setFont(QFont('Microsoft YaHei UI', 12))
                for i, (key, (label, _, _)) in enumerate(POSES.items()):
                    x, y = (i % 4) * 260, (i // 4) * 350
                    pix = pet.sprites[(key, 238)]
                    painter.drawPixmap(x + (260 - pix.width()) // 2, y + 280 - pix.height(), pix)
                    painter.setPen(QColor('#303745'))
                    painter.drawText(x, y + 285, 260, 40, Qt.AlignmentFlag.AlignCenter, label)
                painter.end()
                canvas.save(str(self.root / 'sprites-anime' / 'actions-preview.png'))
            finally:
                pet.tray.hide()
                pet.hide()
                pet.quick_panel.hide()
                if pet.companion_panel:
                    pet.companion_panel.hide()
                m.APP_DIR, m.CONFIG_PATH = old_dir, old_config
                pet.deleteLater()
                self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
