# Pokémon RPG game

Python-based Pokémon RPG game built with Pygame, inspired by the mechanics of Pokémon Mystery Dungeon and the exploration of Stardew Valley. 

## Features:
- Real-time movement and collision system using Pygame
- AI-driven projectile system with optimised vector math.
- Modular architecture for easy expansion.
- Tile-based world rendering with layered assets.

## Project Structure
```
├── src/pokemon_rpg/
│   ├── app.py                 # main game loop
│   ├── data/                  # Pokémon and world registries
│   ├── gameplay/              # entities, combat, moves, and projectiles
│   ├── rendering/             # animation, camera, HUD, and transitions
│   ├── resources/             # controlled asset and map loading
│   └── world/                 # level, map building, and navigation
├── assets/                    # maps and Pokémon sprite sheets
├── benchmarks/                # interactive performance harnesses
└── tests/                     # automated regression suite
```

## Requirements and installation
This project requires **Python 3.11+** and the **uv** package manager.

1. Clone the repository
```
git clone https://github.com/tayyib-saddique/pokemon-rpg.git
cd pokemon-rpg
```
2. Install dependencies
```
uv sync
```
3. Launch the game
```
uv run pokemon-rpg
```

## Tests

Run the automated regression suite with pytest:

```
uv run pytest
```

The interactive projectile stress harness remains available separately:

```
uv run python benchmarks/bubble_beam.py
```

## Gameplay Preview

https://github.com/user-attachments/assets/2f23ddf5-c716-4db2-959b-3147142e4754

## Assets & Credits
### Sprites
The Pokémon sprites used in this project are sourced from the [PMD Sprite Repository](https://sprites.pmdcollab.org/). 
- **Usage:** These assets are used for non-commercial, educational purposes.
- **Credits:** Sprites provided by the PMD Sprite Repository community. Individual artist credits are maintained within the asset folders

### Tilesets
This project uses the following assets which are not included in this repo due to licensing 
- [Asset Alliance](https://itch.io/b/3513/all-in-1-mega-bundle-update-4)
- [Cute Fantasy](https://itch.io/s/116495/cute-fantasy-rpg-sale) (ImageMagick was used to generate spirte sheets from PNG images per directory)
  
To run the game, please place the purchased assets in the `assets/floor_maps/tilesets/` directory.

### License
This project is for educational purposes. Pokémon and all related properties are trademarks of Nintendo, Game Freak, and Creatures Inc.

### AI Attribution
Elements of the projectile system were developed with AI assistance focusing on:
- Vector-based trajectory calculations
- Collision optimisation
  
All AI-assisted code was carefully reviewed, tested, and refactored to ensure performance, accuracy, and maintainability.
