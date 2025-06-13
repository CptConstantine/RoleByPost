# PlayByPostBot

A Discord bot for running play-by-post tabletop RPGs, supporting multiple systems (currently Fate and Mongoose Traveller 2e). PlayByPostBot helps manage character sheets, NPCs, scenes, and dice rolls, making it easy to run and play pbp games on Discord.

---

## Features

- **Character Sheet Management**  
  - Create, edit, and view player characters and NPCs for supported systems. Users can set their "active" character, which is used by default for `/roll` and `/sheet`.
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

- **Reminders**  
  - GMs can remind specific users or roles to post, with a custom message and delay (e.g., "in 2d" or "in 12h").

- **Initiative Management**
  - Supports multiple initiative types:
    - **Generic:** GM sets the order, and turns proceed in that order. Start/End Turn buttons notify the next participant.
    - **Popcorn:** Each participant picks who goes next; at the end of a round, the last person can pick anyone (including themselves) to start the next round.
  - Buttons for starting and ending turns, and display the current round and participant.

---

## Supported Systems

- **Generic**
- **Fate Core**
- **Mongoose Traveller 2e**

---

## Usage and Commands

The following are the commands that are currently available.

### Setup

- `!setgm`  
  Set yourself as a GM for the server. You must be an Admin in the server.

- `!setsystem fate` or `!setsystem mgt2e`  
  Set the RPG system for your server. You must be an Admin in the server.
  
- `!setdefaultskillsfile [.txt file]` or `!setdefaultskills [skill1:0, skill2:0, skill3:1, etc.]`
  (GM only) Set default skills via command or file upload. Skills are validated per system.

### Characters

- `/roll [skill] [attribute]`  
  Roll dice for your active character (PC).
  
- `/createchar [name]`  
  Create a new character.

- `/createnpc [name]`  
  (GM only) Create a new NPC.

- `/setactive [char_name]`  
  Set your active character (PC) for this server.

- `/transferchar [char_name] [new_owner]`  
  (GM only) Transfer a PC to another player.

- `!sheet [char_name]`
  View a character or NPC's sheet. Defaults to your active character if no name is given.

- `/sheet [char_name]`  
  View a character or NPC's sheet with buttons for editing. Defaults to your active character if no name is given.

- `/exportchar [char_name]`  
  Export your character or an NPC (if GM) as a JSON file.

- `/importchar [.json file]`  
  Import a character or NPC from a JSON file.

- `/remind [user] [role] [message] [delay]`  
  (GM only) Remind a user or role to post. Sends a DM if they haven't posted in the server since the reminder. Delay supports formats like `24h`, `2d`, `90m` or `60` for seconds.

### Scene Management

- `!scene`  
  View all NPCs in the current scene.
  
- `!scene_add [npc name]`  
  Add an NPC to the current scene.

- `!scene_remove [npc name]`  
  Remove an NPC from the scene.

- `!scene_clear`  
  Clear all NPCs from the scene.

### Initiative

- `/initiative_start [type] [scene]`  
  Start initiative in the current channel. Type can be "generic" or "popcorn". Scene is optional; uses the current scene if none is provided.
- `/initiative_set_order order="Name1, Name2, Name3"`  
  (GM only) Set the initiative order by providing a comma-separated list of participant names.
- `/initiative_end`  
  End initiative in the current channel.
- `/initiative_add [name]`  
  Add a PC or NPC to the current initiative.
- `/initiative_remove [name]`  
  Remove a PC or NPC from the current initiative.

---

## Features Planned

### Top Priority

- GM can ask for a specific roll with a command
- Commands to make narration and dialogue more interesting
- User can provide an OpenAI API key to gain access to commands that use AI (summarize recent posts, ask rules questions)

### Secondary Priority

- Support for other systems
- System specific commands (ex. starships, travel, and maintenance cost calculations for Traveller; system specific damage calculations)

---

## Contributing

Pull requests and suggestions are welcome! Please open an issue or PR for bug fixes, new features, or system support.

---

### Development Prerequisites

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
