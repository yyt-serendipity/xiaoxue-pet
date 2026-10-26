import math
import unittest
from body_motion import BodyMotion, frame_interval
from desktop_geometry import MotionPosition


class BodyMotionTests(unittest.TestCase):
    def sample(self, motion, now, **changes):
        args = dict(walking=True, phase=.125, speed=180, height=187)
        args.update(changes)
        return motion.sample(now, **args)

    def test_start_and_stop_do_not_drop_body_position(self):
        motion = BodyMotion()
        for i in range(51):
            last = self.sample(motion, i*.02)
        stopped = self.sample(motion, 1., walking=False, phase=0.)
        self.assertEqual(last, stopped)
        for i in range(1, 51):
            current = self.sample(motion, 1+i*.02, walking=False, phase=0.)
        self.assertLess(abs(current.lift), .001)
        self.assertLess(motion.walk_weight, .001)

    def test_envelope_is_independent_of_callback_frequency(self):
        weights = []
        for step in (.02, .04):
            motion = BodyMotion()
            for i in range(round(1/step)+1):
                self.sample(motion, i*step)
            weights.append(motion.walk_weight)
        self.assertAlmostEqual(*weights)

    def test_whole_body_transforms_stay_bounded(self):
        motion = BodyMotion()
        for i in range(500):
            transform = self.sample(motion, i*.02, phase=i*.013 % 1,
                                   jump=i%50/50, action='stretch', amount=i%50/50)
            self.assertTrue(all(math.isfinite(v) for v in transform))
            self.assertLessEqual(abs(transform.rotation), 2.)
            self.assertGreaterEqual(transform.lift, -17.)
            self.assertTrue(.97 < transform.scale_x < 1.01)
            self.assertTrue(.98 < transform.scale_y < 1.06)

    def test_jump_touches_ground_with_zero_end_velocity(self):
        motion = BodyMotion()
        for jump in (0., 1.):
            self.assertAlmostEqual(self.sample(motion, 0., walking=False, jump=jump).lift, 0.)
        near = self.sample(motion, 0., walking=False, jump=.001).lift
        self.assertLess(abs(near/.001), .2)

    def test_subpixel_motion_is_not_lost_in_either_direction(self):
        for sign in (-1, 1):
            position = MotionPosition()
            x, y = 0, 0
            for _ in range(100):
                fx, fy = position.origin(x, y)
                x, y = position.commit(fx+.2*sign, fy+.2*sign)
                dx, dy = position.offset(x, y)
                self.assertLessEqual(abs(dx), .5)
                self.assertLessEqual(abs(dy), .5)
            self.assertEqual((x, y), (20*sign, 20*sign))
            self.assertEqual(position.offset(400, -100), (0., 0.))

    def test_tempo_changes_phase_without_a_pose_jump(self):
        motion = BodyMotion()
        for i in range(51):
            before = self.sample(motion, i*.02, walking=False, tempo=1.)
        unchanged = self.sample(motion, 1., walking=False, tempo=.5)
        self.assertEqual(before, unchanged)
        for i in range(1, 51):
            self.sample(motion, 1+i*.02, walking=False, tempo=.5)
        self.assertAlmostEqual(motion.visual_time, 1.5)

    def test_walking_phase_is_distance_based_not_scaled_twice(self):
        phases = []
        for tempo in (.5, 1.):
            motion = BodyMotion()
            for i in range(51):
                self.sample(motion, i*.02, phase=None, tempo=tempo)
            phases.append(motion.gait_phase)
        self.assertAlmostEqual(*phases)

    def test_hidden_and_sleeping_keep_slow_scheduling(self):
        self.assertEqual(frame_interval(hidden=True, active=True, sleeping=False), 1000)
        self.assertEqual(frame_interval(hidden=False, active=False, sleeping=True), 100)
        self.assertEqual(frame_interval(hidden=False, active=False, sleeping=False), 33)
        self.assertEqual(frame_interval(hidden=False, active=True, sleeping=False), 20)


if __name__ == '__main__':
    unittest.main()
