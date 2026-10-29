import os

import pygame
import pytest


@pytest.fixture
def display(monkeypatch):
    """A headless display, for code that converts images or reads the screen."""
    monkeypatch.setitem(os.environ, "SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.display.set_mode((64, 64))
    yield pygame.display.get_surface()
    pygame.display.quit()
