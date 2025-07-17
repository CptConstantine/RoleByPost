# RoleByPost

A Discord bot for running play-by-post tabletop RPGs, supporting multiple systems (currently Generic, Fate and Mongoose Traveller 2e). RoleByPost helps manage character sheets, NPCs, scenes, dice rolls, and inventory management, making it easy to run and play pbp games on Discord.

Discord server **invite link**: https://discord.com/oauth2/authorize?client_id=1379606934470135998&permissions=398291364880&scope=bot%20applications.commands

---

## Features

- **Character Sheet Management**  
  - Create, edit, and view player characters and NPCs for supported systems. Users can set their "active" character, which is used by default for `/roll` and `/char sheet`.
  - System-specific fields and validation (e.g., Fate aspects, Traveller skills).
  - Import/export characters as JSON files for easy transfer between servers.

- **Entity Connections System**
  - Create links between characters, NPCs, and other entities.
    - Currently allows for inventory and loot management
  - Support for control of companions (and speak as them through the narration system)

- **Inventory and Container Management**
  - Keep track of items and store them in containers or in a character's inventory.
  - GMs can create "loot containers" that players can take from and give items to
  - Inventory tracking for characters with item links
  - GMs can hide loot from players and reveal it when the time is right.

- **Scene Management**  
  - Create and manage multiple scenes and keep track of NPCs and notes
  - Switch between scenes to organize different locations or encounters
  - Attach images to scenes for maps or set dressing.
  - System-specific scene details (Fate aspects, Traveller environmental conditions)
  - Pin scenes to channels for easy reference by all players

- **Customizable Skills**  
  - GMs can set a default skill list via .txt file upload.

- **Dice Rolling**  
  - Supports standard dice notation (e.g., `2d6+3`) and Fate/Fudge dice (`4df+1`).
  - System-specific UI for modifying rolls with skills and attributes.

- **Story Recaps**
  - AI-powered summaries of recent gameplay to help players catch up.
  - On-demand recaps for any timeframe.
  - Automatic scheduled recaps to keep everyone in the loop.

- **Rules Management**
  - Ask an AI about the rules of the game system you are using.
  - GM can add homebrew rules that are used in the context of each query.

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
  - Players can speak as their companions and other controlled entities
  - GMs can speak as NPCs with custom display names
  - GMs can provide narration with special formatting
  - Automatically restricted from out of character channels to maintain immersion

- **Channel Management**
  - Configure channels as In-Character (IC), Out-of-Character (OOC), GM Only, or Unrestricted
  - Commands are automatically restricted based on channel type to maintain immersion and organization
  - Keeps roleplay focused in IC channels while organizing administrative tasks in appropriate channels

---

## Supported Systems

- **Generic**
- **Fate Core/Condensed/Accelerated**
- **Mongoose Traveller 1e/2e**

---

## Usage and Commands

The following are the commands that are currently available.

### Help

- `/help guide`  
  Show a guide to all help topics and commands.
- `/help getting-started`  
  General help for starting out with the bot.
- `/help characters`
  Help for character management commands.
- `/help entities`
  Help for entity management commands.
- `/help rolling`
  Help for rolling commands for dice and checks.
- `/help scenes` 
  Help for scene management commands.
- `/help initiative`
  Help for initiative management commands.
- `/help recaps`
  Help for recap generation and management.
- `/help reminders` 
  Help for reminder setup and management.
- `/help rules`
  Help for rules questions and homebrew management.
- `/help setup` 
  Help for setup and configuration commands.
- `/help narration` 
  Help for character speech and narration commands.
- `/help ai`
  Help for AI-powered commands and features.

### Setup

- `/setup system [system]`  
  Set the RPG system for your server. You must be an Admin in the server.

- `/setup gm-role [role]`  
  Set a Discord role as the GM role for the server. Anyone with this role will have GM permissions. You must be an Admin.

- `/setup player-role [role]`  
  Set a Discord role as the player role for the server. Anyone with this role will be considered a player. You must be an Admin.
  
- `/setup default-skills-file [.txt file]` or `/setup default-skills [skill1:0, skill2:0, skill3:1, etc.]`  
  (GM only) Set default skills via command or file upload. Skills are validated per system (if the system has skills).

- `/setup openai set-api-key [api_key]`  
  (GM only) Set the OpenAI API key used for generating recaps and answering rules questions. Required for all AI functionality.

- `/setup openai remove-api-key`  
  (GM only) Removes your api key if it was set.

- `/setup openai status`  
  Check if an OpenAI API key is configured for this server and see available AI features.

- `/setup channel type [channel] [channel_type]`  
  (GM only) Configure channel restrictions. Set channels as IC (in-character), OOC (out-of-character), GM Only, or Unrestricted.

- `/setup channel status`  
  (GM only) View all channel permission configurations for this server.

- `/setup status`  
  (GM only) View comprehensive server bot configuration and statistics including roles, active scenes, character counts, feature settings, channel restrictions, and more.

### Characters

- `/char create pc [name] [owner]`  
  Create a new player character. Optionally specify an owner entity for companions, minions, etc.

- `/char create npc [name] [owner]`  
  (GM only) Create a new NPC. Optionally specify an owner entity.

- `/char sheet [char_name]`  
  View a character or NPC's sheet with buttons for editing. Defaults to your active character if no name is given.

- `/char list [show_npcs] [owned_by] [show_links]`  
  List characters and NPCs. Filter by owner or show link details.

- `/char delete [char_name]`  
  Delete a character or NPC.

- `/char export [char_name]`  
  Export your character or an NPC (if GM) as a JSON file.

- `/char import [.json file]`  
  Import a character or NPC from a JSON file.

- `/char transfer [char_name] [new_owner]`  
  (GM only) Transfer a PC to another player.

- `/char switch [char_name]`  
  Set your active character (PC) for this server.

- `/char set-nickname [full_char_name] [nickname]`  
  Set or remove a nickname for a character. Leave nickname blank to remove all nicknames.

- `/char nickname-list [full_char_name]`  
  List all nicknames for a character.

- `/char set-avatar [char_name] [avatar_url] [file]`  
  Set your character's avatar image with either a url OR a file upload.

### Entities

- `/entity create [entity_type] [name]`  
  Create a new entity (item, container, etc.).

- `/entity list [owner_entity] [entity_type] [show_links]`  
  List entities with optional filtering by owner or type. Show link details if requested.

- `/entity view [entity_name]`  
  View detailed information about an entity including its links and interactive editing interface.

- `/entity rename [entity_name] [new_name]`  
  Rename an entity.

- `/entity delete [entity_name]`  
  Delete an entity. Entities that own other entities cannot be deleted until links are transferred.

- `/entity delete-all [entity_type]`
  Delete all entities that don't have any links to other entities. Optionally, delete all of a specific type of entity.

### Connections

- `/link create [from_entity] [to_entity] [link_type] [description]`  
  Create a link between two entities.

- `/link remove [from_entity] [to_entity] [link_type]`  
  Remove a link between two entities. Leave link_type blank to remove all links.

- `/link list [entity_name]`  
  List all links for an entity, showing both incoming and outgoing links.

- `/link transfer [possessed_entity] [new_owner]`  
  (GM only) Transfer possession of an entity to another entity. Removes existing possession links and creates new ones.

**Permissions:**
- Only GMs can create/remove ownership and control links
- Users can only create links involving entities they own
- GMs can see all entities, users see only their own entities in autocomplete

### Rolling

- `/roll check [roll_parameters] [difficulty]`  
  Roll dice for your active character with optional parameters. The roll_parameters field has intelligent autocomplete that adapts to your server's RPG system, offering relevant skills, attributes, and modifiers.

- `/roll custom`
  Open the system specific roll interface for your character.

- `/roll request [chars_to_roll] [roll_parameters] [difficulty]`  
  (GM only) Request players to roll with specified parameters. Both character names and roll parameters have smart autocomplete. System-specific UIs allow players to adjust skills/attributes.

### Scene Management

- `/scene create [name]`  
  (GM only) Create a new scene with the given name.

- `/scene set-image [name] [image_url] [file]`
  (GM only) Sets the image for a scene. Defaults to the active scene. Use an image url OR upload a file.

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
  
- `/scene add-npc [npc name] [scene_name]`  
  (GM only) Add an NPC to a scene. If scene_name is not provided, adds to the active scene.

- `/scene remove-npc [npc name] [scene_name]`  
  (GM only) Remove an NPC from a scene. If scene_name is not provided, removes from the active scene.

- `/scene clear`  
  (GM only) Clear all NPCs from the current active scene.

- `/scene pin`  
  (GM only) Pin the current scene to the channel for easy reference. The pin automatically updates when scenes change.

- `/scene unpin`  
  (GM only) Disable scene pinning and remove all pinned scene messages.

### Initiative

- `/init start [type] [scene]`  
  (GM only) Start initiative in the current channel. Scene and type are optional.

- `/init end`  
  (GM only) End initiative in the current channel.

- `/init add-npc [name]`  
  (GM only) Add a PC or NPC to the current initiative.

- `/init remove-npc [name]`  
  (GM only) Remove a PC or NPC from the current initiative.

- `/init set-default [type]`  
  (GM only) Set the default initiative type for this server.

### Story Recaps

- `/recap generate [days] [private]`  
  Generate a summary of recent game events. Specify how many days to include and whether the recap should be private.

- `/recap set-auto [enabled] [channel] [days_interval] [days_to_include]`  
  (GM only) Configure automatic story recaps. Enable or disable them, set which channel they post to, how often they run, and how many days of history they include.

- `/recap auto-status`  
  Check the current automatic recap settings for this server, including next scheduled recap time.

- `/recap auto-now`  
  (GM only) Force an automatic recap to be generated immediately.

### Reminders

- `/reminder send [user] [role] [message] [delay]`  
  (GM only) Remind a user or role to post. Sends a DM if they haven't posted in the server since the reminder. Delay supports formats like `24h`, `2d`, `90m` or `60` for seconds.

- `/reminder set [user] [time] [message]`  
  (GM only) Set a reminder for yourself or another user with a custom message and time delay.

- `/reminder set-auto [enabled] [delay]`  
  (GM only) Configure automatic reminders when users are mentioned. Set whether they're enabled and/or the delay before sending.

- `/reminder auto-opt-out [opt_out]`  
  Opt out of receiving automatic reminders when mentioned. Set to false to opt back in.

- `/reminder auto-status`  
  Check the current automatic reminder settings for this server.

### Rules Questions

- `/rules question [prompt]`  
  Ask a question about the rules of your current RPG system. Uses AI to provide answers based on the system and any homebrew rules set by the GM.

- `/rules homebrew [rule_name] [rule_text]`  
  (GM only) Add or update a homebrew rule for the server. These rules are used as context when answering rules questions.

- `/rules homebrew-list`  
  View all homebrew rules and clarifications for this server.

- `/rules homebrew-remove [rule_name]`  
  (GM only) Remove a homebrew rule from the server.

### Character Speech and Narration

This bot provides special message prefixes that transform regular text messages into formatted character speech or GM narration:

- **Character Nicknames**  
  Set up nicknames for easier narration with `/char set-nickname [full_char_name] [nickname]`.
  Once set, you can use nicknames in place of the character's full name.

- **Character Avatars**  
  Set your character's avatar with `/char set-avatar [char_name] [url] [file]` to enhance the immersion.
  This shows up in any narration message for the character.

- **Editing narration posts**
  `right-click message -> Apps -> Edit Narration`
  Fix typos or leave it blank to delete it altogether.

- **Speaking as Your Character**  
  `pc::Your character's message here`  
  Displays a message as your currently active character, with their avatar if set.

- **Speaking as a Specific Character/Companion**  
  `Character Name::Message content`  
  Use the character's full name or any nickname they have.
  Example: `Bob the Brave::I'll take the first watch.`
  Example: `Bobby::I'll take the first watch.` (if "Bobby" is Bob the Brave's nickname)

- **Using Aliases for Characters/Companions**  
  `Character Name::Display Name::Message content`  
  Use a custom display name for the message.
  Example: `Bob the Brave::The Brave One::Ready for action!`

- **GM: Speaking as NPCs**  
  `NPC Name::Message content`  
  Displays a message as the specified NPC, with their avatar if available.
  Example: `Bartender::What'll it be, stranger?`

- **GM: Using Aliases for NPCs**  
  `NPC Name::Alias::Message content` or `npc::NPC Name::Alias::Message content`  
  Lets GMs use an alias for the NPC in this specific message.
  Example: `Bartender::Barkeep::What'll it be?`

- **GM: On-the-fly NPCs**  
  If `npc::` is at the beginning of the message, the bot creates a temporary character for the message even if the NPC doesn't exist in the database.

- **GM Narration**  
  `gm::Your narration text here`  
  Creates a purple-bordered embed with the GM's avatar for scene descriptions and narration.

**Channel Restrictions:** Narration commands (`pc::`, `npc::`, `gm::`) are automatically blocked in **Out-of-Character (OOC)** channels to maintain immersion. Use them in **In-Character (IC)** or **Unrestricted** channels.

For more detailed help, use `/help narration`.

### Fate System Commands

- `/fate scene aspects`  
  Show all aspects in the current scene including game aspects, scene aspects, zone aspects, and character aspects. GMs can see hidden aspects while players see only visible ones.

**Interactive Aspect Management:**
When viewing a scene in a Fate game, GMs have access to these Fate-specific features:
- **Edit Game Aspects:** Manage server-wide aspects that persist across scenes
- **Edit Scene Aspects:** Manage aspects specific to the current scene  
- **Edit Zones:** Create and manage zone lists and zone-specific aspects

All aspect editing supports:
- Hidden aspects (surround with `*asterisks*`)
- Free invokes (add `[number]` after aspect name)

---

## Features Planned

- Convert some commands to context menu commands
- System specific features
  - Traveller: starships, travel, and maintenance cost calculations
  - Container management features (weight/bulk, item type filtering, etc.)
- Support for other systems

---

## License

This project is licensed under the MIT License.

---

## Disclaimer

This bot is not affiliated with any RPG publisher. Please respect the licenses and copyrights of the games you use.

## Private Policy

https://github.com/CptConstantine/RoleByPost/blob/main/PRIVACY.md

## Terms of Service

https://github.com/CptConstantine/RoleByPost/blob/main/TERMS.md
