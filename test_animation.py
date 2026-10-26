import random
import unittest
from animation import MotionClock, blend
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication


class Clock:
    now = 0.
    def __call__(self):
        return self.now


class AnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_blending_preserves_color_and_opacity(self):
        pix = QPixmap(2, 2)
        pix.fill(QColor(60, 90, 150))
        for fraction in (.2, .5, .8):
            rgba = blend(pix, pix, fraction).toImage().pixelColor(0, 0).getRgb()
            for actual, expected in zip(rgba, (60, 90, 150, 255)):
                self.assertLessEqual(abs(actual - expected), 2)

    def setUp(self):
        self.clock = Clock()
        self.motion = MotionClock(self.clock, random.Random(1))

    def test_walk_speed_and_pause(self):
        self.motion.sample('walk', 90, 100)
        for _ in range(5):
            self.clock.now += .1
            self.motion.sample('walk', 90, 100)
        self.assertAlmostEqual(self.motion.phase, .5)
        self.clock.now += .1
        self.motion.sample('walk', 0, 100)
        self.assertAlmostEqual(self.motion.phase, .5)

    def test_wave_returns_to_rest_without_loop_snap(self):
        self.motion.sample('wave', 0, 238)
        self.clock.now = .22 * 12
        a, b, _ = self.motion.sample('wave', 0, 238)
        self.assertEqual((a, b), (0, 0))
        self.clock.now = .22 * 14
        a, b, fraction = self.motion.sample('wave', 0, 238)
        self.assertEqual(a, 0)
        self.assertAlmostEqual(fraction, 0)
        self.clock.now += .44
        self.assertEqual(self.motion.sample('wave', 0, 238)[:2], (0, 0))

    def test_blink_closes_then_opens_and_waits(self):
        self.motion.sample('idle', 0, 238)
        self.clock.now = self.motion.next_blink
        self.motion.sample('idle', 0, 238)
        self.clock.now += .12
        a, b, _ = self.motion.sample('idle', 0, 238)
        self.assertEqual((a, b), (2, 2))
        self.clock.now += .2
        self.assertEqual(self.motion.sample('idle', 0, 238), (0, 0, 0.))
        self.assertGreater(self.motion.next_blink, self.clock.now + 2.9)

    def test_new_gestures_return_to_start_without_loop_snap(self):
        for action in ('drink',):
            self.motion.action = None
            self.clock.now = 0
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (0, 1))
            self.clock.now = 1.15
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (3, 3))
            self.clock.now = 3.42
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (0, 0))

    def test_heart_path_lifts_holds_then_lowers_without_per_frame_stops(self):
        from animation import HEART_ACTIONS, heart_sample
        for action in HEART_ACTIONS:
            self.motion.action = None
            self.clock.now = 0
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (0, 1))
            self.clock.now = 1.3
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (4, 4))
            self.clock.now = 3.6
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (0, 0))
        progress = []
        for i in range(116):
            a, b, f = heart_sample(i / 100)
            progress.append(a + (b-a)*f)
        self.assertEqual(progress, sorted(progress))
        for t in (.4, .575, .75):
            a,b,f=heart_sample(t-.001); left=a+(b-a)*f
            a,b,f=heart_sample(t+.001); right=a+(b-a)*f
            self.assertGreater(right-left, .004)

    def test_heart_source_pair_and_cache_are_bounded(self):
        from animation import Animator, HEART_ACTIONS
        from sprite_store import SpriteStore
        from pathlib import Path
        root=Path(__file__).parent/'sprites-anime'
        animator=Animator(root,[238],clock=self.clock)
        sprites=SpriteStore(root,238)
        for action in HEART_ACTIONS:
            animator.timeline.action=None
            for i in range(80):
                self.clock.now += .05
                animator.render((action,238,1),sprites,0)
                bank=animator.frames[action][238]
                self.assertLessEqual(len(bank.resident),2)
                self.assertLessEqual(animator.cache_bytes,2*1024*1024)
            self.assertEqual(sum(k in HEART_ACTIONS for k in animator.frames),1)
        animator.release()
        self.assertFalse(animator.frames)
        self.assertEqual(animator.cache_bytes,0)

    def test_slow_gestures_reach_rest_before_pose_timeout(self):
        # Lowering must finish even at the slowest setting; no clipped last frames.
        durations = dict(wave=3.08, drink=3.42, heart_finger=3.6,
                         heart_chest=3.6, heart_overhead=3.6)
        for action, duration in durations.items():
            self.clock.now = 0.
            self.motion.action = None
            self.motion.rate = .75
            self.motion.sample(action, 0, 187)
            self.clock.now = (duration-.05)/.75
            self.assertEqual(self.motion.sample(action, 0, 187)[:2], (0, 0), action)

    def test_sleep_cannot_trigger_blink(self):
        self.clock.now = 100
        self.assertEqual(self.motion.sample('sleep', 0, 238), (0, 0, 0.))

    def test_offline_motion_reverse_and_endpoints(self):
        from animation import MotionBank
        from pathlib import Path
        directory = Path(__file__).parent/'sprites-anime/prepared/187/action-motion/wave'
        bank = MotionBank(directory)
        for a, b in ((0, 1), (3, 4), (5, 1)):
            for fraction in (0., .125, .4, .8, 1.):
                left = bank.resolve(a, b, fraction)
                right = bank.resolve(b, a, 1-fraction)
                self.assertEqual(left[:2], right[:2])
                self.assertAlmostEqual(left[2], right[2])
            first, _, _ = bank.resolve(a, b, 0.)
            last, _, _ = bank.resolve(a, b, 1.)
            bank.select(first, last)
            self.assertEqual(bank[first].toImage(), bank[bank.keyframes[str(a)]].toImage())
            self.assertEqual(bank[last].toImage(), bank[bank.keyframes[str(b)]].toImage())

    def test_walk_changes_before_the_old_last_fifth_transition_window(self):
        from animation import Animator
        from sprite_store import SpriteStore
        from pathlib import Path
        root = Path(__file__).parent/'sprites-anime'
        sprites = SpriteStore(root, 187)
        animator = Animator(root, [187], clock=self.clock)
        first = animator.render(('walk1', 187, 1), sprites, 100).toImage()
        # 40 ms is only 19% of this step, previously a completely held pose.
        self.clock.now += .04
        second = animator.render(('walk1', 187, 1), sprites, 100).toImage()
        self.assertNotEqual(first, second)

    def test_offline_actions_keep_two_frames_and_release_inactive_banks(self):
        from animation import Animator, MotionBank
        from sprite_store import SpriteStore
        from pathlib import Path
        root = Path(__file__).parent/'sprites-anime'
        sprites = SpriteStore(root, 238)
        animator = Animator(root, [238], clock=self.clock)
        for pose in ('walk1', 'wave', 'drink', '正面'):
            for _ in range(150):
                self.clock.now += .02
                animator.render((pose, 238, 1), sprites, 100)
                for action, sizes in animator.frames.items():
                    bank = sizes[238]
                    if isinstance(bank, MotionBank):
                        self.assertLessEqual(len(bank.resident), 2)
                        if action in ('walk', 'wave') and action != ('walk' if pose == 'walk1' else pose):
                            self.assertFalse(bank.resident)
                self.assertLessEqual(animator.cache_bytes, 2*1024*1024)
        self.assertNotIn('drink', animator.frames)
        animator.release()
        self.assertFalse(animator.frames)

    def test_settle_finishes_a_passing_pose(self):
        self.motion.sample('walk', 200, 187)
        self.clock.now += .1
        self.motion.sample('walk', 200, 187)
        start, target, fraction = self.motion.sample('settle', 0, 187)
        self.assertIn(target, (2, 6))
        self.assertEqual(fraction, 0.)
        self.clock.now += .18
        self.assertEqual(self.motion.sample('settle', 0, 187), (start, target, 1.))

    def test_wave_rate_shortens_cycle_without_speeding_blink(self):
        self.motion.rate = 2.
        self.motion.sample('wave', 0, 238)
        self.clock.now = .11
        self.assertEqual(self.motion.sample('wave', 0, 238)[:2], (1, 2))
        self.clock.now = 3.08 / 2
        self.assertEqual(self.motion.sample('wave', 0, 238)[0], 0)


if __name__ == '__main__':
    unittest.main()
