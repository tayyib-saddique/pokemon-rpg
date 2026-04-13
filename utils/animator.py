"""
Animator — handles frame advancement, attack speed, trigger detection,
and loop completion for sprite animations.

Usage:
    self.animator = Animator(self.animations)
    result = self.animator.update(status, dt)
    self.image = result.image
    if result.triggered: ...
    if result.finished: ...
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class AnimationResult:
    image: Any = None
    triggered: bool = False  # True on the mid-point trigger frame
    finished: bool = False  # True when the animation looped


class Animator:
    ATTACK_SPEED = 20
    WALK_SPEED = 8

    def __init__(self, animations: dict):
        self.animations = animations
        self.frame_index = 0.0

    def update(self, status: str, dt: float) -> AnimationResult:
        frames = self.animations.get(status)
        if not frames:
            return AnimationResult()

        is_attack = "_shoot" in status or "_strike" in status
        speed = self.ATTACK_SPEED if is_attack else self.WALK_SPEED

        old = int(self.frame_index)
        self.frame_index += speed * dt
        new = int(self.frame_index)

        trigger_frame = len(frames) // 2
        triggered = "_shoot" in status and old < trigger_frame <= new

        finished = False
        if new >= len(frames):
            self.frame_index = 0.0
            finished = is_attack

        image = frames[min(int(self.frame_index), len(frames) - 1)]
        return AnimationResult(image=image, triggered=triggered, finished=finished)

    def reset(self):
        self.frame_index = 0.0
