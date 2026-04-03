# Pokémon RPG game

Python-based Pokémon RPG game built with Pygame, inspired by the mechanics of Pokémon Mystery Dungeon and the exploration of Stardew Valley. 

## Features:
- Real-time movement and collision system using Pygame
- AI-driven projectile system with optimised vector math.
- Modular architecture for easy expansion.
- Tile-based world rendering with layered assets.

## Project Structure
```
├── constants/         # Pokémon stats, moves, and game data
├── graphics/          # tilesets and maps
├── projectiles/       # AI-optimised projectiles
├── tests/             # stress-tests
├── utils/             # utility functions
├── level.py           # world manager, handling map loading and managing the player
├── player.py          # handles player logic including sprite animation and movement
├── settings.py        # controls game settings
├── hud.py             # UI/HUD rendering logic
└── main.py            # Main game loop and entry point
```

## Requirements and installation
To run this game, you will need Python 3.x and the Pygame library installed on your machine. 

1. Clone the repository
```
git clone https://github.com/tayyib-saddique/pokemon-rpg.git
cd pokemon-rpg
```
2. Install dependencies
```
pip install -r requirements.txt
```
3. Launch the game
```
python main.py
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
  
To run the game, please place the purchased assets in the `/graphics/floormaps/tilesets/` directory.

### License
This project is for educational purposes. Pokémon and all related properties are trademarks of Nintendo, Game Freak, and Creatures Inc.

### AI Attribution
Elements of the projectile system were developed with AI assistance focusing on:
- Vector-based trajectory calculations
- Collision optimisation
  
All AI-assisted code was carefully reviewed, tested, and refactored to ensure performance, accuracy, and maintainability.
