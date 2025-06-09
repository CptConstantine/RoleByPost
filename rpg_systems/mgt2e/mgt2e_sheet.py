import discord
from character_sheets.base_sheet import BaseSheet
from data import repo


class MGT2ESheet(BaseSheet):
    DEFAULT_SKILLS = {
        "Admin": -3,
        "Advocate": -3,
        "Animals (Handling)": -3,
        "Animals (Veterinary)": -3,
        "Animals (Training)": -3,
        "Art (Performer)": -3,
        "Art (Holography)": -3,
        "Art (Instrument)": -3,
        "Art (Visual Media)": -3,
        "Art (Write)": -3,
        "Astrogation": -3,
        "Athletics (Dexterity)": -3,
        "Athletics (Endurance)": -3,
        "Athletics (Strength)": -3,
        "Broker": -3,
        "Carouse": -3,
        "Deception": -3,
        "Diplomat": -3,
        "Drive (Hovercraft)": -3,
        "Drive (Mole)": -3,
        "Drive (Track)": -3,
        "Drive (Walker)": -3,
        "Drive (Wheel)": -3,
        "Electronics (Comms)": -3,
        "Electronics (Computers)": -3,
        "Electronics (Remote Ops)": -3,
        "Electronics (Sensors)": -3,
        "Engineer (M-drive)": -3,
        "Engineer (J-drive)": -3,
        "Engineer (Life Suport)": -3,
        "Engineer (Power)": -3,
        "Explosives": -3,
        "Flyer (Airship)": -3,
        "Flyer (Grav)": -3,
        "Flyer (Ornithopter)": -3,
        "Flyer (Rotor)": -3,
        "Flyer (Wing)": -3,
        "Gambler": -3,
        "Gunner (Turret)": -3,
        "Gunner (Ortillery)": -3,
        "Gunner (Screen)": -3,
        "Gunner (Capital)": -3,
        "Gun Combat (Archaic)": -3,
        "Gun Combat (Energy)": -3,
        "Gun Combat (Slug)": -3,
        "Heavy Weapons (Artillery)": -3,
        "Heavy Weapons (Portable)": -3,
        "Heavy Weapons (Vehicle)": -3,
        "Investigate": -3,
        "Jack of All Trades": -3,
        "Language (Galanglic)": -3,
        "Language (Vilany)": -3,
        "Language (Zdetl)": -3,
        "Language (Oynprith)": -3,
        "Language (Trokh)": -3,
        "Language (Gvegh)": -3,
        "Leadership": -3,
        "Mechanic": -3,
        "Medic": -3,
        "Melee (Unarmed)": -3,
        "Melee (Blade)": -3,
        "Melee (Bludgeon)": -3,
        "Melee (Natural)": -3,
        "Navigation": -3,
        "Persuade": -3,
        "Pilot (Small Craft)": -3,
        "Pilot (Spacecraft)": -3,
        "Pilot (Capital Ships)": -3,
        "Recon": -3,
        "Science (Archaeology)": -3,
        "Science (Astronomy)": -3,
        "Science (Biology)": -3,
        "Science (Chemistry)": -3,
        "Science (Cosmology)": -3,
        "Science (Cybernetics)": -3,
        "Science (Economics)": -3,
        "Science (Genetics)": -3,
        "Science (History)": -3,
        "Science (Linguistics)": -3,
        "Science (Philosophy)": -3,
        "Science (Physics)": -3,
        "Science (Planetology)": -3,
        "Science (Psionicology)": -3,
        "Science (Psychology)": -3,
        "Science (Robotics)": -3,
        "Science (Xenology)": -3,
        "Seafarer (Ocean Ships)": -3,
        "Seafarer (Personal)": -3,
        "Seafarer (Sail)": -3,
        "Seafarer (Submarine)": -3,
        "Stealth": -3,
        "Steward": -3,
        "Streetwise": -3,
        "Survival": -3,
        "Tactics (Military)": -3,
        "Tactics (Naval)": -3,
        "Vacc Suit": -3
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
        trained_skills = self.get_trained_skills(skills)
        if trained_skills:
            sorted_skills = sorted(trained_skills.items(), key=lambda x: (x[0]))
            skill_lines = []
            for k, v in sorted_skills:
                # Show value (0 or higher) for trained
                skill_lines.append(f"**{k}**: {v}")
            # Split into multiple fields if too long
            chunk = ""
            count = 1
            for line in skill_lines:
                if len(chunk) + len(line) + 1 > 1024:
                    if count == 1:
                        embed.add_field(name=f"Skills", value=chunk.strip(), inline=False)
                    chunk = ""
                    count += 1
                chunk += line + "\n"
            if chunk:
                embed.add_field(name=f"Skills {count}", value=chunk.strip(), inline=False)
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
    
    def roll(self, character, *, skill=None, attribute=None, formula=None):
        import random, re

        if formula:
            arg = formula.replace(" ", "").lower()
            fudge_pattern = r'(\d*)d[fF]([+-]\d+)?'
            fudge_match = re.fullmatch(fudge_pattern, arg)
            if fudge_match:
                num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
                modifier = int(fudge_match.group(2)) if fudge_match.group(2) else 0
                rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
                symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
                total = sum(rolls) + modifier
                response = f'🎲 Fudge Rolls: `{" ".join(symbols)}`'
                if modifier:
                    response += f' {"+" if modifier > 0 else ""}{modifier}'
                response += f'\n🧮 Total: {total}'
                return response
            pattern = r'(\d*)d(\d+)([+-]\d+)?'
            match = re.fullmatch(pattern, arg)
            if match:
                num_dice = int(match.group(1)) if match.group(1) else 1
                die_size = int(match.group(2))
                modifier = int(match.group(3)) if match.group(3) else 0
                if num_dice > 100 or die_size > 1000:
                    return "😵 That's a lot of dice. Try fewer."
                rolls = [random.randint(1, die_size) for _ in range(num_dice)]
                total = sum(rolls) + modifier
                response = f'🎲 Rolled: {rolls}'
                if modifier:
                    response += f' {"+" if modifier > 0 else ""}{modifier}'
                response += f'\n🧮 Total: {total}'
                return response
            return "❌ Invalid formula. Use like `2d6+3` or `4df+1`."

        if not skill or not attribute:
            return "❌ Please specify both a skill and an attribute."
        skills = character.get("skills", {})
        skill_mod = self.get_skill_modifier(skills, skill)
        attr_val = character.get("attributes", {}).get(attribute.upper(), 0)
        attr_mod = self.get_attribute_modifier(attr_val)
        rolls = [random.randint(1, 6) for _ in range(2)]
        total = sum(rolls) + skill_mod + attr_mod
        response = (
            f'🎲 2d6: {rolls} + **{skill}** ({skill_mod}) + **{attribute.upper()}** mod ({attr_mod})\n'
            f'🧮 Total: {total}'
        )
        return response

    def get_trained_skills(self, skills: dict) -> dict:
        """
        Returns a dict of all trained skills and specialties (value may be 0 or higher).
        If a skill or any of its specialties is >= 0, all specialties and the base skill are trained.
        """
        trained_groups = set()
        # Step 1: Find all skill groups with any specialty at >= 0
        for skill_name, value in skills.items():
            if "(" in skill_name and ")" in skill_name and value >= 0:
                group = skill_name.split("(", 1)[0].strip()
                trained_groups.add(group)
        # Also, if a non-specialty skill is >= 0, it's trained (and so are its specialties)
        for skill_name, value in skills.items():
            if "(" not in skill_name and value >= 0:
                trained_groups.add(skill_name.strip())

        trained_skills = {}
        for skill_name, value in skills.items():
            # Specialties: trained if group is trained
            if "(" in skill_name and ")" in skill_name:
                group = skill_name.split("(", 1)[0].strip()
                if group in trained_groups:
                    trained_skills[skill_name] = value
            # Non-specialty: trained if in trained_groups
            elif skill_name in trained_groups:
                trained_skills[skill_name] = value
        return trained_skills

    def is_skill_trained(self, skills: dict, skill_name: str) -> bool:
        """
        Returns True if the skill or its group is trained (i.e., present at >= 0).
        """
        # Check for specialty
        if "(" in skill_name and ")" in skill_name:
            group = skill_name.split("(", 1)[0].strip()
            # Trained if any specialty or the group is present at >= 0
            for k, v in skills.items():
                if (k.startswith(group) and v >= 0) or (k == group and v >= 0):
                    return True
            return False
        else:
            # Non-specialty: trained if present at >= 0 or any specialty is present at >= 0
            if skills.get(skill_name, None) is not None and skills[skill_name] >= 0:
                return True
            for k, v in skills.items():
                if k.startswith(skill_name + " (") and v >= 0:
                    return True
            return False

    def get_skill_modifier(self, skills: dict, skill_name: str) -> int:
        """
        Returns the modifier for a skill:
        - If trained (present at >= 0), modifier is the value (even if 0)
        - If untrained, modifier is -3
        """
        if self.is_skill_trained(skills, skill_name):
            return skills.get(skill_name, 0)
        else:
            return -3

    def get_attribute_modifier(self, attr_val) -> int:
        if attr_val <= 0:
            return -3
        elif attr_val <= 2:
            return -2
        elif attr_val <= 5:
            return -1
        elif attr_val <= 8:
            return 0
        elif attr_val <= 11:
            return 1
        elif attr_val <= 14:
            return 2
        else:
            return 3