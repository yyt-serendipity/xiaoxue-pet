import unittest
from PySide6.QtCore import QRect
from desktop_geometry import clamp_position, dock_position, nearby_edge, movement_step


class DesktopGeometryTests(unittest.TestCase):
    def test_negative_monitor_coordinates(self):
        screen = QRect(-1920, -200, 1920, 1080)
        self.assertEqual(clamp_position(-3000, -500, 300, 250, screen), (-1920, -200))
        self.assertEqual(dock_position(-500, 0, 300, 250, screen, 'right'), (-308, 0))
        self.assertEqual(dock_position(-500, 0, 300, 250, screen, 'bottom'), (-500, 622))

    def test_drag_snap_threshold(self):
        screen = QRect(0, 0, 1920, 1080)
        self.assertEqual(nearby_edge(8, 400, 300, 250, screen), 'left')
        self.assertIsNone(nearby_edge(500, 400, 300, 250, screen))

    def test_braking_no_overshoot(self):
        distance, speed = 200., 0.
        speeds = []
        for _ in range(1000):
            step, speed = movement_step(distance, speed, 380, .02)
            self.assertLessEqual(step, distance)
            distance -= step
            speeds.append(speed)
            if distance <= .001:
                break
        self.assertLessEqual(distance, .001)
        self.assertLess(speeds[0], max(speeds))
        self.assertLess(speeds[-1], max(speeds))

    def test_small_work_area(self):
        self.assertEqual(clamp_position(999, 999, 300, 250, QRect(10, 20, 200, 100)), (10, 20))
