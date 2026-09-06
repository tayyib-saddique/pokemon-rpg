from pokemon_rpg.rendering.animation import Animator


def test_shoot_triggers_when_crossing_midpoint():
    animator = Animator({"right_shoot": ["a", "b", "c", "d"]})
    result = animator.update("right_shoot", 0.1)

    assert result.triggered
    assert not result.finished
    assert result.image == "c"


def test_attack_finishes_and_resets_after_last_frame():
    animator = Animator({"down_strike": ["a", "b"]})
    result = animator.update("down_strike", 0.1)

    assert result.finished
    assert result.image == "a"
    assert animator.frame_index == 0.0


def test_walk_loop_does_not_report_attack_completion():
    animator = Animator({"down_walk": ["a", "b"]})
    result = animator.update("down_walk", 0.25)

    assert not result.finished
    assert result.image == "a"


def test_unknown_animation_returns_empty_result():
    result = Animator({}).update("missing", 1.0)

    assert result.image is None
    assert not result.triggered
    assert not result.finished
