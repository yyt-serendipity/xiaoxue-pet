"""Logical-screen-coordinate helpers, including monitors left of the primary."""
import math


class MotionPosition:
    """Keep fractional motion across integer window moves; resync after dragging/docking."""
    def __init__(self):
        self.logical = None
        self.window = None

    def origin(self, x, y):
        if self.window != (x, y):
            self.logical = (float(x), float(y))
            self.window = (x, y)
        return self.logical

    def commit(self, x, y):
        self.logical = (x, y)
        self.window = (round(x), round(y))
        return self.window

    def offset(self, x, y):
        logical = self.origin(x, y)
        return logical[0]-x, logical[1]-y


def clamp_position(x, y, width, height, geometry):
    return (max(geometry.left(), min(round(x), geometry.right() + 1 - width)),
            max(geometry.top(), min(round(y), geometry.bottom() + 1 - height)))


def dock_position(x, y, width, height, geometry, edge, margin=8):
    x, y = clamp_position(x, y, width, height, geometry)
    if edge == 'left':
        x = geometry.left() + margin
    elif edge == 'right':
        x = geometry.right() + 1 - width - margin
    elif edge == 'top':
        y = geometry.top() + margin
    elif edge == 'bottom':
        y = geometry.bottom() + 1 - height - margin
    return clamp_position(x, y, width, height, geometry)


def nearby_edge(x, y, width, height, geometry, threshold=24):
    distances = {'left': abs(x - geometry.left()),
                 'right': abs(x + width - geometry.right() - 1),
                 'top': abs(y - geometry.top()),
                 'bottom': abs(y + height - geometry.bottom() - 1)}
    edge = min(distances, key=distances.get)
    return edge if distances[edge] <= threshold else None


def movement_step(distance, speed, maximum, dt):
    """Bounded acceleration and braking distance, with no target overshoot."""
    desired = min(maximum, math.sqrt(max(0, 2 * 900 * distance)))
    change = max(-1200 * dt, min(1000 * dt, desired - speed))
    speed = max(0., speed + change)
    return min(distance, speed * dt), speed
