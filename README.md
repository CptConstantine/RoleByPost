# PlayByPostBot

A Discord bot for running play-by-post tabletop RPGs, supporting multiple systems (currently Generic, Fate and Mongoose Traveller 2e). PlayByPostBot helps manage character sheets, NPCs, scenes, and dice rolls, making it easy to run and play pbp games on Discord.

---

## Features

- **Character Sheet Management**  
  - Create, edit, and view player characters and NPCs for supported systems. Users can set their "active" character, which is used by default for `/roll` and `/character sheet`.
  - System-specific fields and validation (e.g., Fate aspects, Traveller skills).
  - Import/export characters as JSON files for easy transfer between servers.

- **Scene Management**  
  - Create and manage multiple scenes and keep track of NPCs and notes
  - Switch between scenes to organize different locations or encounters
  - System-specific scene details (Fate aspects, Traveller environmental conditions)
  - Pin scenes to channels for easy reference by all players

- **Customizable Skills**  
  - GMs can set default skill lists per server and system, via .txt file upload.

- **Dice Rolling**  
  - Supports standard dice notation (e.g., `2d6+3`) and Fate/Fudge dice (`4df+1`).
  - System-specific UI for modifying rolls with skills and attributes.

- **Story Recaps**
  - AI-powered summaries of recent gameplay to help players catch up.
  - On-demand recaps for any timeframe.
  - Automatic scheduled recaps to keep everyone in the loop.

- **Reminders**  
  - GMs can remind specific users or roles to post, with a custom message and delay (e.g., "in 2d" or "in 12h").
  - Automatic reminders when users are mentioned but haven't responded.
  - Users can opt out of automatic reminders if they prefer.

- **Initiative Management**
  - Supports multiple initiative types:
    - **Generic:** GM sets the order, and turns proceed in that order. Start/End Turn buttons notify the next participant.
    - **Popcorn:** Each participant picks who goes next; at the end of a round, the last person can pick anyone (including themselves) to start the next round.
  - GMs can set the initiative order directly from the initiative tracker.
  - Buttons for starting and ending turns, and displays the current round and participants.

- **Character Speech and Narration**
  - Players can speak as their characters with formatted messages and avatars
  - GMs can speak as NPCs with custom display names
  - GMs can provide narration with special formatting

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
  Set a Discord role as the GM role for the server. Anyone with this role will have GM permissions. You must be an Admin.

- `/setup playerrole [role]`  
  Set a Discord role as the player role for the server. Anyone with this role will be considered a player. You must be an Admin.
  
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

- `/roll check [roll_parameters]`  
  Roll dice for your active character with optional parameters.

- `/roll custom`
  Open the system specific roll interface for your character.

- `/roll request [chars_to_roll] [roll_parameters] [difficulty]`  
  (GM only) Request players to roll with specified parameters. System-specific UIs allow players to adjust skills/attributes.

### Scene Management

- `/scene create [name]`  
  (GM only) Create a new scene with the given name.

- `/scene list`  
  (GM only) View all available scenes.

- `/scene switch [scene_name]`  
  (GM only) Switch to a different scene. This automatically unpins any old scene messages and pins the new scene to the current channel.

- `/scene rename [current_name] [new_name]`  
  (GM only) Rename an existing scene.

- `/scene delete [scene_name]`  
  (GM only) Delete a scene and all its associated data.

- `/scene view [scene_name]`  
  View any scene (active or inactive). If no scene name is provided, shows the current active scene.
  
- `/scene addnpc [npc name] [scene_name]`  
  (GM only) Add an NPC to a scene. If scene_name is not provided, adds to the active scene.

- `/scene removenpc [npc name] [scene_name]`  
  (GM only) Remove an NPC from a scene. If scene_name is not provided, removes from the active scene.

- `/scene clear`  
  (GM only) Clear all NPCs from the current active scene.

- `/scene pin`  
  (GM only) Pin the current scene to the channel for easy reference. The pin automatically updates when scenes change.

- `/scene off`  
  (GM only) Disable scene pinning and remove all pinned scene messages.

### Initiative

- `/initiative start [type] [scene]`  
  Start initiative in the current channel. Scene and type are optional.

- `/initiative end`  
  End initiative in the current channel.

- `/initiative add [name]`  
  Add a PC or NPC to the current initiative.

- `/initiative remove [name]`  
  Remove a PC or NPC from the current initiative.

- `/initiative default [type]`  
  Set the default initiative type for this server.

### Story Recaps

- `/recap generate [days] [private]`  
  Generate a summary of recent game events. Specify how many days to include and whether the recap should be private.

- `/recap setkey [api_key]`  
  (GM only) Set the OpenAI API key used for generating recaps. Required for all recap functionality.

- `/recap setauto [enabled] [channel] [days_interval] [days_to_include]`  
  (GM only) Configure automatic story recaps. Enable or disable them, set which channel they post to, how often they run, and how many days of history they include.

- `/recap autostatus`  
  Check the current automatic recap settings for this server, including next scheduled recap time.

- `/recap autonow`  
  (GM only) Force an automatic recap to be generated immediately.

### Reminders

- `/reminder send [user] [role] [message] [delay]`  
  (GM only) Remind a user or role to post. Sends a DM if they haven't posted in the server since the reminder. Delay supports formats like `24h`, `2d`, `90m` or `60` for seconds.

- `/reminder set [user] [time] [message]`  
  (GM only) Set a reminder for yourself or another user with a custom message and time delay.

- `/reminder setauto [enabled] [delay]`  
  (GM only) Configure automatic reminders when users are mentioned. Set whether they're enabled and/or the delay before sending.

- `/reminder autooptout [opt_out]`  
  Opt out of receiving automatic reminders when mentioned. Set to false to opt back in.

- `/reminder autostatus`  
  Check the current automatic reminder settings for this server.

### Character Speech and Narration

This bot provides special message prefixes that transform regular text messages into formatted character speech or GM narration:

- **Speaking as Your Character**  
  `pc::Your character's message here`  
  Displays a message as your currently active character, with their avatar if set.

- **GM: Speaking as NPCs**  
  `npc::NPC Name::Message content`  
  Displays a message as the specified NPC, with their avatar if available.

- **GM: Using Aliases**  
  `npc::NPC Name::Alias::Message content`  
  Lets GMs use an alias for the NPC in this specific message.

- **GM: On-the-fly NPCs**  
  Even if the NPC doesn't exist in the database, the bot creates a temporary character for the message.

- **GM Narration**  
  `gm::Your narration text here`  
  Creates a purple-bordered embed with the GM's avatar for scene descriptions and narration.

- **Character Avatars**  
  Set your character's avatar with `/character setavatar [url]` to enhance the immersion.

For more detailed help, use `/character narration`.

---

## Features Planned

### Top Priority

- Add ability for players to manage multiple characters (for companions, minions, hirelings, etc.) and optionally speak as them for narration
- Inventory system to track equipment

### Secondary Priority

- Manage channels so that certain commands can only be used in specific channels to prevent clutter
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