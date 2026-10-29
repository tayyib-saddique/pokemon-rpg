import pygame

from pokemon_rpg.data.pokemon import SPRITE_SHEETS


class Generic(pygame.sprite.Sprite):
    def __init__(self, pos, surface, groups):
        super().__init__(groups)
        self.image = surface
        self.rect = self.image.get_rect(topleft=pos)


def make_hitbox(pokemon, rect):
    """Collision box centred on `rect`.

    Uses the pokemon's configured "hitbox" size when it has one, otherwise
    half the sprite frame. Frame padding varies between sheets, so the
    fallback can come out wider than a one-tile corridor.
    """
    size = SPRITE_SHEETS.get(pokemon, {}).get("hitbox")
    if size is None:
        return rect.inflate(-rect.width // 2, -rect.height // 2)
    hitbox = pygame.Rect((0, 0), size)
    hitbox.center = rect.center
    return hitbox
