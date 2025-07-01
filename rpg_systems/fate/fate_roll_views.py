# rpg_systems/fate/fate_roll_views.py
import discord
from discord import ui, SelectOption
from core.shared_views import FinalizeRollButton, PaginatedSelectView, RollModifiersView
from rpg_systems.fate.fate_roll_modifiers import FateRollModifiers
from data.repositories.repository_factory import repositories

class FateRollModifiersView(RollModifiersView):
    """
    Fate-specific roll modifiers view that includes a button to select skills.
    """
    def __init__(self, roll_formula_obj: FateRollModifiers, difficulty: int = None):
        self.character = None
        super().__init__(roll_formula_obj, self.character, difficulty)
        # Add a button for skill selection
        self.add_item(FateSelectSkillButton(self, roll_formula_obj.skill))
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))
    
    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class FateSelectSkillButton(ui.Button):
    """Button that opens a skill selection menu when clicked"""
    def __init__(self, parent_view: FateRollModifiersView, selected_skill: str = None):
        super().__init__(
            label=selected_skill if selected_skill else "Select Skill",
            style=discord.ButtonStyle.primary,
            row=3
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return
        
        skills = character.skills if hasattr(character, 'skills') else {}
        skill_options = [SelectOption(label=f"{k} (+{v})" if v >= 0 else f"{k} ({v})", 
                                      value=k) 
                         for k, v in sorted(skills.items(), key=lambda x: (-x[1], x[0]))]
        
        if not skill_options:
            await interaction.response.send_message("❌ Your character has no skills to select.", ephemeral=True)
            return
        
        async def on_skill_selected(view, interaction2, skill):
            # Update the roll formula with the selected skill
            self.label = skill
            self.parent_view.roll_formula_obj.skill = skill
            skill_value = character.skills.get(skill, 0)
            await interaction2.response.edit_message(
                content=f"Selected skill: **{skill}** (+{skill_value if skill_value >= 0 else skill_value})",
                view=self.parent_view
            )
        
        await interaction.response.send_message(
            "Select a skill for your roll:",
            view=PaginatedSelectView(skill_options, on_skill_selected, interaction.user.id, prompt="Select a skill:"),
            ephemeral=True
        )