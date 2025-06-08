import discord
from character_sheets.base_sheet import BaseSheet
from data import repo


class MGT2ESheet(BaseSheet):
    DEFAULT_SKILLS = {
        "Admin": 0,
        "Advocate": 0,
        "Animals (Handling)": 0,
        "Animals (Veterinary)": 0,
        "Animals (Training)": 0,
        "Art (Performer)": 0,
        "Art (Holography)": 0,
        "Art (Instrument)": 0,
        "Art (Visual Media)": 0,
        "Art (Write)": 0,
        "Astrogation": 0,
        "Athletics (Dexterity)": 0,
        "Athletics (Endurance)": 0,
        "Athletics (Strength)": 0,
        "Broker": 0,
        "Carouse": 0,
        "Deception": 0,
        "Diplomat": 0,
        "Drive (Hovercraft)": 0,
        "Drive (Mole)": 0,
        "Drive (Track)": 0,
        "Drive (Walker)": 0,
        "Drive (Wheel)": 0,
        "Electronics (Comms)": 0,
        "Electronics (Computers)": 0,
        "Electronics (Remote Ops)": 0,
        "Electronics (Sensors)": 0,
        "Engineer (M-drive)": 0,
        "Engineer (J-drive)": 0,
        "Engineer (Life Suport)": 0,
        "Engineer (Power)": 0,
        "Explosives": 0,
        "Flyer (Airship)": 0,
        "Flyer (Grav)": 0,
        "Flyer (Ornithopter)": 0,
        "Flyer (Rotor)": 0,
        "Flyer (Wing)": 0,
        "Gambler": 0,
        "Gunner (Turret)": 0,
        "Gunner (Ortillery)": 0,
        "Gunner (Screen)": 0,
        "Gunner (Capital)": 0,
        "Gun Combat (Archaic)": 0,
        "Gun Combat (Energy)": 0,
        "Gun Combat (Slug)": 0,
        "Heavy Weapons (Artillery)": 0,
        "Heavy Weapons (Portable)": 0,
        "Heavy Weapons (Vehicle)": 0,
        "Investigate": 0,
        "Jack of All Trades": 0,
        "Language (Galanglic)": 0,
        "Language (Vilany)": 0,
        "Language (Zdetl)": 0,
        "Language (Oynprith)": 0,
        "Language (Trokh)": 0,
        "Language (Gvegh)": 0,
        "Leadership": 0,
        "Mechanic": 0,
        "Medic": 0,
        "Melee (Unarmed)": 0,
        "Melee (Blade)": 0,
        "Melee (Bludgeon)": 0,
        "Melee (Natural)": 0,
        "Navigation": 0,
        "Persuade": 0,
        "Pilot (Small Craft)": 0,
        "Pilot (Spacecraft)": 0,
        "Pilot (Capital Ships)": 0,
        "Recon": 0,
        "Science (Archaeology)": 0,
        "Science (Astronomy)": 0,
        "Science (Biology)": 0,
        "Science (Chemistry)": 0,
        "Science (Cosmology)": 0,
        "Science (Cybernetics)": 0,
        "Science (Economics)": 0,
        "Science (Genetics)": 0,
        "Science (History)": 0,
        "Science (Linguistics)": 0,
        "Science (Philosophy)": 0,
        "Science (Physics)": 0,
        "Science (Planetology)": 0,
        "Science (Psionicology)": 0,
        "Science (Psychology)": 0,
        "Science (Robotics)": 0,
        "Science (Xenology)": 0,
        "Seafarer (Ocean Ships)": 0,
        "Seafarer (Personal)": 0,
        "Seafarer (Sail)": 0,
        "Seafarer (Submarine)": 0,
        "Stealth": 0,
        "Steward": 0,
        "Streetwise": 0,
        "Survival": 0,
        "Tactics (Military)": 0,
        "Tactics (Naval)": 0,
        "Vacc Suit": 0
    }
    SYSTEM_SPECIFIC_CHARACTER = {
        "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
        "skills": {}
    }
    SYSTEM_SPECIFIC_NPC = {
        "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
        "skills": {}
    }

    def apply_defaults(self, character_dict, is_npc=False, guild_id=None):
        system_defaults = self.SYSTEM_SPECIFIC_NPC if is_npc else self.SYSTEM_SPECIFIC_CHARACTER
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    skills = repo.get_default_skills(guild_id, "mgt2e")
                default_skills = dict(skills) if skills else dict(self.DEFAULT_SKILLS)
                # Only add skills that are not already present
                character_dict.setdefault("skills", {})
                for skill, val in default_skills.items():
                    if skill not in character_dict["skills"]:
                        character_dict["skills"][skill] = val
            else:
                if key not in character_dict:
                    character_dict[key] = value

    @staticmethod
    def parse_and_validate_skills(skills_str):
        """Parse a skills string like 'Admin:0, Gun Combat:1' into a dict. Add MGT2E-specific validation here."""
        skills_dict = {}
        for entry in skills_str.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        # Add any MGT2E-specific validation here if needed
        return skills_dict

    def format_full_sheet(self, character: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"{character.get('name', 'Traveller')}",
            color=discord.Color.dark_teal()
        )

        # --- Attributes ---
        attributes = character.get("attributes", {})
        if attributes:
            attr_lines = [
                f"**STR**: {attributes.get('STR', 0)}   **DEX**: {attributes.get('DEX', 0)}   **END**: {attributes.get('END', 0)}",
                f"**INT**: {attributes.get('INT', 0)}   **EDU**: {attributes.get('EDU', 0)}   **SOC**: {attributes.get('SOC', 0)}"
            ]
            embed.add_field(name="Attributes", value="\n".join(attr_lines), inline=False)
        else:
            embed.add_field(name="Attributes", value="None", inline=False)

        # --- Skills ---
        skills = character.get("skills", {})
        if skills:
            sorted_skills = sorted(skills.items(), key=lambda x: (-x[1], x[0]))
            skill_lines = [f"**{k}**: {v}" for k, v in sorted_skills]
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
        else:
            embed.add_field(name="Skills", value="None", inline=False)

        # --- Notes ---
        notes = character.get("notes", "")
        embed.add_field(name="Notes", value=notes if notes else "_No notes_", inline=False)

        return embed

    def format_npc_scene_entry(self, npc, is_gm):
        lines = [f"**{npc.get('name', 'NPC')}**"]
        if is_gm and npc.get("notes"):
            lines.append(f"**Notes:** *{npc['notes']}*")
        return "\n".join(lines)