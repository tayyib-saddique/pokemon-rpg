"""
CameraGroup — handles camera offset, sprite bucketing, and depth-sorted drawing.
"""
import pygame


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def draw(self, player):
        self._update_offset(player)

        floor_sprites, shadow_sprites, depth_sprites = self._bucket_sprites(player)

        for sprite in floor_sprites + shadow_sprites:
            self._blit(sprite)

        depth_sprites.append(player)
        depth_sprites.sort(key=lambda s: getattr(s, "ground_y", s.rect.bottom))

        for sprite in depth_sprites:
            self._blit(sprite)

    def _update_offset(self, player):
        """Centre the camera on the player."""
        self.offset.x = player.rect.centerx - self.display_surface.get_width() // 2
        self.offset.y = player.rect.centery - self.display_surface.get_height() // 2

    def _bucket_sprites(self, player):
        """Split sprites into floor, shadow, and depth buckets."""
        floor_sprites = []
        shadow_sprites = []
        depth_sprites = []

        for sprite in self.sprites():
            if sprite is player:
                continue
            layer = getattr(sprite, "layer_name", "")
            if "Floor" in layer or "Terrain" in layer:
                floor_sprites.append(sprite)
            elif "Shadow" in layer:
                shadow_sprites.append(sprite)
            else:
                depth_sprites.append(sprite)

        return floor_sprites, shadow_sprites, depth_sprites

    def _blit(self, sprite):
        if hasattr(sprite, "draw"):
            sprite.draw(self.display_surface, self.offset)
        else:
            self.display_surface.blit(sprite.image, sprite.rect.topleft - self.offset)
