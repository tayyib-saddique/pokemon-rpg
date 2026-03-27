## Pokemon RPG game

Python-based Pokemon RPG game built with Pygame, taking inspiration from Stardew Valley and Pokemon Mystery Dungeons. 

### Project Structure

```
├── constants/         # Pokémon stats, moves, and game data
├── graphics/          # tilesets and maps
├── projectiles/       # AI-optimised projectiles
├── tests/             # stress-tests (pytest has not been used in this project given the nature of pygame)
├── utils/             # utility functions
├── level.py           # world manager, handling map loading and managing the player
├── player.py          # handles player logic including sprite animation and movement
├── settings.py        # controls game settings
└── main.py            # Main game loop and entry point
```

### Requirements and installation
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

### License
This project is for educational purposes. Pokémon and all related properties are trademarks of Nintendo, Game Freak, and Creatures Inc.

### Assets & Credits

### Sprites
The Pokémon sprites used in this project are sourced from the [PMD Sprite Repository](https://sprites.pmdcollab.org/). 
- **Usage:** These assets are used for non-commercial, educational purposes.
- **Credits:** Sprites provided by the PMD Sprite Repository community. Individual artist credits are maintained within the asset folders

### Tilesets
This project uses the following assets which are not included in this repo due to licensing. https://vectoraith.itch.io/asset-alliance-modern-gold-mine


To run the game, please place the purchased assets in the `/graphics/floormaps/tilesets/` directory.  

### AI Attribution
Core logic within the `projectiles/` directory was generated with AI assistance to optimise vector physics and trajectory math. 