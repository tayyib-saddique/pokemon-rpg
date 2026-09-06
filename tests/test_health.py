from pokemon_rpg.gameplay.combat.health import Health


def test_defaults_to_full_health():
    health = Health(max_hp=100)

    assert health.current == 100
    assert health.ratio == 1.0
    assert not health.is_dead


def test_damage_is_clamped_at_zero():
    health = Health(max_hp=100)
    health.take_damage(150)

    assert health.current == 0
    assert health.is_dead
    assert health.ratio == 0.0


def test_healing_is_clamped_at_maximum():
    health = Health(max_hp=100, current=40)
    health.heal(80)

    assert health.current == 100


def test_zero_max_health_has_safe_ratio():
    assert Health(max_hp=0).ratio == 0.0
