# PlayByPostBot

A Discord bot for running play-by-post tabletop RPGs, supporting multiple systems (currently Fate and Mongoose Traveller 2e). PlayByPostBot helps manage character sheets, NPCs, scenes, and dice rolls, making it easy to run and play RPGs asynchronously on Discord.

---

## Features

- **Character Sheet Management**  
  - Create, edit, and view player characters and NPCs for supported systems.
  - System-specific fields and validation (e.g., Fate aspects, Traveller skills).
  - Import/export characters as JSON files for easy transfer between servers.

- **Scene Management**  
  - Add or remove NPCs from the current scene.
  - View a summary of all NPCs in the scene.

- **Customizable Skills**  
  - GMs can set default skill lists per server and system, via text or file upload.
  - Supports `.txt` file uploads for easy skill list customization.

- **Dice Rolling**  
  - Supports standard dice notation (e.g., `2d6+3`) and Fate/Fudge dice (`4df+1`).

- **Slash Commands and Classic Commands**  
  - Most features are available via both classic (`!command`) and slash (`/command`) commands.

---

## Supported Systems

- **Fate Core** (aspects, skills, stress, consequences, fate points)
- **Mongoose Traveller 2e** (attributes, skills, notes)

---

## Usage

### Basic Commands

- `!setgm`  
  Set yourself as a GM for the server.

- `!setsystem fate` or `!setsystem mgt2e`  
  Set the RPG system for your server.
  
- `!setdefaultskillsfile [.txt file]` or `!setdefaultskills [skill1:0, skill2:0, skill3:1, etc.]`
  (GM only) Set default skills via command or file upload. Skills are validated per system.

- `!createchar [name]`  
  Create a new character.

- `!createnpc [name]`  
  (GM only) Create a new NPC.

- `!sheet [name]` or `/sheet [name]`  
  View a character or NPC's sheet.

- `/exportchar [name]`  
  Export your character or an NPC (if GM) as a JSON file.

- `/importchar <.json file>`  
  Import a character or NPC from a JSON file.

- `!roll 2d6+3` or `!roll 4df+1`  
  Roll dice.

### Scene Management

- `!scene_add [npc name]`  
  Add an NPC to the current scene.

- `!scene_remove [npc name]`  
  Remove an NPC from the scene.

- `!scene_clear`  
  Clear all NPCs from the scene.

- `!scene`  
  View all NPCs in the current scene.

---

## Features Planned

- Support for other systems
- Ability to have multiple characters per discord user
- System specific commands (ex. starships, travel, and maintenence cost calculations for Traveller)

---

## Contributing

Pull requests and suggestions are welcome! Please open an issue or PR for bug fixes, new features, or system support.

---

## Getting Started

### Prerequisites

- Developed on Python 3.12.10
- A Discord bot token ([how to create one](https://discord.com/developers/applications))
- [python-dotenv](https://pypi.org/project/python-dotenv/) for environment variable management

### Installation for Development

1. **Clone the repository**
   ```sh
   git clone https://github.com/CptConstantine/PlayByPostBot.git
   cd PlayByPostBot
   ```

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up your environment**
   - Create a `.env` file in the project root:
     ```
     DISCORD_BOT_TOKEN=your-bot-token-here
     ```

4. **Initialize the database**
   ```sh
   python data/init_db.py
   ```

5. **Run the bot**
   ```sh
   python main.py
   ```

---

## License

This project is licensed under the MIT License.

---

## Disclaimer

This bot is not affiliated with any RPG publisher. Please respect the licenses and copyrights of the games you use.
