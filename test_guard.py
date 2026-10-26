import unittest
from game_guard import avoidance_reason, covers_monitor

class GuardTests(unittest.TestCase):
    def test_system_states(self):
        for state in (1, 2, 3, 4, 6):
            self.assertTrue(avoidance_reason(state=state, own_window=True))
        for state in (5, 7):
            self.assertFalse(avoidance_reason(state=state))

    def test_fullscreen_and_maximized(self):
        monitor = (-1920, 0, 0, 1080)
        self.assertTrue(avoidance_reason(client=monitor, monitor=monitor))
        self.assertFalse(avoidance_reason(client=(-1920, 30, 0, 1040), monitor=monitor))
        self.assertFalse(avoidance_reason(client=monitor, monitor=monitor, window_class='WorkerW'))
        self.assertFalse(avoidance_reason(client=monitor, monitor=monitor, own_window=True))

    def test_custom_rules_exact(self):
        self.assertTrue(avoidance_reason(name='OBS64.exe', extra_apps=' obs64.exe ; wemeetapp.exe'))
        self.assertFalse(avoidance_reason(name='obs64-helper.exe', extra_apps='obs64.exe'))
        self.assertFalse(avoidance_reason(name='chrome.exe'))
        self.assertTrue(avoidance_reason(name='cs2.exe'))
        self.assertTrue(avoidance_reason(name='wemeetapp.exe'))
        self.assertTrue(avoidance_reason(name='obs64.exe'))

