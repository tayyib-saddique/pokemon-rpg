import pygame

def load_pmd_sheet(path, frame_w, frame_h):
    sheet = pygame.image.load(path).convert_alpha()
    cols = sheet.get_width() // frame_w

    directions = ['down', 'down_left', 'left', 'up_left',
                  'up', 'up_right', 'right', 'down_right']

    animations = {}
    for row, direction in enumerate(directions):
        frames = []
        for col in range(cols):
            frame = sheet.subsurface(pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h))
            frames.append(frame)
        animations[direction + '_idle'] = [frames[0]]
        animations[direction] = frames
    return animations