# PlayByPostBot

A Discord bot for running play-by-post tabletop RPGs, supporting multiple systems (currently Generic, Fate and Mongoose Traveller 2e). PlayByPostBot helps manage character sheets, NPCs, scenes, and dice rolls, making it easy to run and play pbp games on Discord.

---

## Features

- **Character Sheet Management**  
  - Create, edit, and view player characters and NPCs for supported systems. Users can set their "active" character, which is used by default for `/roll` and `/character sheet`.
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
  - System-specific UI for modifying rolls with skills and attributes.

- **Reminders**  
  - GMs can remind specific users or roles to post, with a custom message and delay (e.g., "in 2d" or "in 12h").

- **Initiative Management**
  - Supports multiple initiative types:
    - **Generic:** GM sets the order, and turns proceed in that order. Start/End Turn buttons notify the next participant.
    - **Popcorn:** Each participant picks who goes next; at the end of a round, the last person can pick anyone (including themselves) to start the next round.
  - Initiative participants are robustly managed as dataclasses for reliability.
  - GMs can set the initiative order at any time with `/initiative order`.
  - Buttons for starting and ending turns, and display the current round and participant.

---

## Supported Systems

- **Generic**
- **Fate Core/Condensed/Accelerated**
- **Mongoose Traveller 1e/2e**

---

## Usage and Commands

The following are the commands that are currently available.

### Setup

- `/setup system [system]`  
  Set the RPG system for your server. You must be an Admin in the server.

- `/setup gmrole [role]`  
  Set all members of a Discord role as GMs for the server. You must be an Admin.

- `/setup playerrole [role]`  
  Set all members of a Discord role as players for the server. You must be an Admin.
  
- `/setup defaultskillsfile [.txt file]` or `/setup defaultskills [skill1:0, skill2:0, skill3:1, etc.]`  
  (GM only) Set default skills via command or file upload. Skills are validated per system (if the system has skills).

### Characters

- `/character create pc [name]`  
  Create a new player character.

- `/character create npc [name]`  
  (GM only) Create a new NPC.

- `/character sheet [char_name]`  
  View a character or NPC's sheet with buttons for editing. Defaults to your active character if no name is given.

- `/character export [char_name]`  
  Export your character or an NPC (if GM) as a JSON file.

- `/character import [.json file]`  
  Import a character or NPC from a JSON file.

- `/character transfer [char_name] [new_owner]`  
  (GM only) Transfer a PC to another player.

- `/character switch [char_name]`  
  Set your active character (PC) for this server.

### Rolling

- `/roll [skill] [attribute] [modifier] [difficulty]`  
  Roll dice for your active character (PC) with optional parameters.

- `/roll request [chars_to_roll] [skill] [attribute] [modifier] [difficulty]`  
  (GM only) Request players to roll with specified parameters. System-specific UIs allow players to adjust skills/attributes.

### Scene Management

- `/scene`  
  View all NPCs in the current scene.
  
- `/scene add [npc name]`  
  Add an NPC to the current scene.

- `/scene remove [npc name]`  
  Remove an NPC from the scene.

- `/scene clear`  
  Clear all NPCs from the scene.

### Initiative

- `/initiative start [type] [scene]`  
  Start initiative in the current channel. Type can be "generic" or "popcorn". Scene is optional.

- `/initiative order [Name1, Name2, Name3, etc.]`  
  (GM only) Set the initiative order by providing a comma-separated list of participant names.

- `/initiative end`  
  End initiative in the current channel.

- `/initiative add [name]`  
  Add a PC or NPC to the current initiative.

- `/initiative remove [name]`  
  Remove a PC or NPC from the current initiative.

- `/initiative default [type]`  
  Set the default initiative type for this server.

### Reminders

- `/reminder send [user] [role] [message] [delay]`  
  (GM only) Remind a user or role to post. Sends a DM if they haven't posted in the server since the reminder. Delay supports formats like `24h`, `2d`, `90m` or `60` for seconds.

---

## Features Planned

### Top Priority

- Optionally set automatic reminders when someone is mentioned
- Manage channels so that certain commands can only be used in specific channels to prevent clutter
- Commands to make narration and dialogue more interesting
- User can provide an OpenAI API key to gain access to commands that use AI (summarize recent posts, ask rules questions)
- Inventory system to track equipment

### Secondary Priority

- Avatars for characters
- System specific commands (ex. starships, travel, and maintenance cost calculations for Traveller; system specific damage calculations)
- Support for other systems

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