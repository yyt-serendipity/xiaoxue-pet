"""Small, whole-character transforms; no images, bones or runtime interpolation model."""
import math
from typing import NamedTuple


class BodyTransform(NamedTuple):
    rotation: float
    lift: float
    scale_x: float
    scale_y: float


class BodyMotion:
    def __init__(self):
        self.last_time = None
        self.walk_weight = 0.
        self.gait_phase = 0.
        self.visual_time = 0.

    def sample(self, now, *, walking, phase, speed, height, pose=None,
               dragging=False, jump=0., action=None, amount=0., tempo=1.):
        dt = 0. if self.last_time is None else min(.1, max(0., now-self.last_time))
        self.last_time = now
        # Accumulate phase so changing tempo never jumps the current pose.
        visual_dt = dt * max(0., tempo)
        self.visual_time += visual_dt
        goal = min(1., max(0., speed)/max(1., height*.65)) if walking else 0.
        self.walk_weight += (goal-self.walk_weight) * -math.expm1(-visual_dt/.12)
        if walking:
            self.gait_phase = phase if phase is not None else (self.gait_phase + dt*max(0., speed)/max(1., height*.9)) % 1.
        weight = self.walk_weight
        quiet = .15 if pose == 'sleep' else .3 if pose else 1.
        if dragging:
            quiet = 0.
        breath = math.sin(self.visual_time*2.5)
        rotation = ((1-weight)*math.sin(self.visual_time*2.5)*1.25*quiet
                    + weight*math.sin(self.gait_phase*math.tau)*2.)
        # A raised cosine has no cusp at the step contact; fade out the last gait.
        lift = -.5*(1-math.cos(self.gait_phase*math.tau*2))*3.5*(height/187)*weight
        jump = min(1., max(0., jump))
        lift -= math.sin(math.pi*jump)**2 * 13*(height/187)
        sx, sy = 1+.004*breath*quiet, 1+.014*breath*quiet
        progress = 1-min(1., max(0., amount))
        envelope = math.sin(math.pi*progress)**2
        if action == 'sway':
            rotation += math.sin(math.tau*progress)*envelope*6
        elif action == 'stretch':
            sx -= .018*envelope
            sy += .035*envelope
        return BodyTransform(rotation, lift, sx, sy)


def frame_interval(*, hidden, active, sleeping):
    """Preserve the 50 Hz active cap, with 30 Hz visible idle and slow hidden checks."""
    return 1000 if hidden else 20 if active else 100 if sleeping else 33
