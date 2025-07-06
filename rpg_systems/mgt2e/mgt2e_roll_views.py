import discord
import discord.ui as ui
from core.shared_views import FinalizeRollButton, PaginatedSelectView, RollFormulaView
from rpg_systems.mgt2e.mgt2e_roll_formula import MGT2ERollFormula, BoonBane
from data.repositories.repository_factory import repositories

class MGT2ERollFormulaView(RollFormulaView):
    """
    MGT2E-specific roll modifiers view that includes buttons to select skills and attributes.
    """
    def __init__(self, roll_formula_obj: MGT2ERollFormula, difficulty: int = None):
        self.character = None
        super().__init__(roll_formula_obj, self.character, difficulty)
        # Add buttons for skill and attribute selection
        self.add_item(MGT2ESelectSkillButton(self, roll_formula_obj.skill))
        self.add_item(MGT2ESelectAttributeButton(self, roll_formula_obj.attribute))
        self.add_item(MGT2EBoonBaneButton(self))
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))
    
    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class MGT2ESelectSkillButton(ui.Button):
    """Button that opens a skill category selection menu when clicked"""
    def __init__(self, parent_view: MGT2ERollFormulaView, selected_skill: str = None):
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
        
        from rpg_systems.mgt2e.mgt2e_character import get_skill_categories
        skills = character.skills if hasattr(character, 'skills') else {}
        categories = get_skill_categories(skills)
        category_options = [discord.SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]
        
        if not category_options:
            await interaction.response.send_message("❌ Your character has no skill categories.", ephemeral=True)
            return
        
        async def on_category_selected(view, interaction: discord.Interaction, category):
            skills_in_cat = categories[category]
            
            # If there's only one skill in this category and it's the same as the category name,
            # it means this is a standalone skill with no specialties
            if len(skills_in_cat) == 1 and skills_in_cat[0] == category:
                # Skip the skill selection step and directly update the roll formula
                self.label = category
                self.parent_view.roll_formula_obj.skill = category
                skill_mod = character.get_skill_modifier(skills, category)
                await interaction.response.edit_message(
                    content=f"Selected skill: **{category}** ({skill_mod})",
                    view=self.parent_view
                )
            else:
                # Multiple skills or specialties, continue with skill selection
                skill_options = [discord.SelectOption(label=f"{skill} ({skills.get(skill, -3)})", value=skill) 
                                for skill in sorted(skills_in_cat)]
                
                async def on_skill_selected(view2, interaction2, skill):
                    # Update the roll formula with the selected skill
                    self.label = skill
                    self.parent_view.roll_formula_obj.skill = skill
                    skill_mod = character.get_skill_modifier(skills, skill)
                    await interaction2.response.edit_message(
                        content=f"Selected skill: **{skill}** ({skill_mod})",
                        view=self.parent_view
                    )
                
                await interaction.response.edit_message(
                    content=f"Select a skill in {category}:",
                    view=PaginatedSelectView(
                        skill_options, 
                        on_skill_selected, 
                        interaction.user.id, 
                        prompt=f"Select a skill in {category}:"
                    )
                )
        
        await interaction.response.send_message(
            "Select a skill category:",
            view=PaginatedSelectView(
                category_options, 
                on_category_selected, 
                interaction.user.id, 
                prompt="Select a skill category:"
            ),
            ephemeral=True
        )

class MGT2ESelectAttributeButton(ui.Button):
    """Button that opens an attribute selection menu when clicked"""
    def __init__(self, parent_view: MGT2ERollFormulaView, selected_attribute: str = None):
        super().__init__(
            label=selected_attribute if selected_attribute else "Select Attribute",
            style=discord.ButtonStyle.secondary,
            row=3
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return
        
        attributes = character.attributes if hasattr(character, 'attributes') else {}
        attr_options = []
        
        for k, v in sorted(attributes.items()):
            mod = character.get_attribute_modifier(v)
            attr_options.append(discord.SelectOption(
                label=f"{k}: {v} (MOD: {mod})",
                value=k
            ))
        
        if not attr_options:
            await interaction.response.send_message("❌ Your character has no attributes.", ephemeral=True)
            return
        
        async def on_attr_selected(view, interaction2, attr):
            # Update the roll formula with the selected attribute
            self.label = attr
            self.parent_view.roll_formula_obj.attribute = attr
            attr_val = attributes.get(attr, 0)
            attr_mod = character.get_attribute_modifier(attr_val)
            await interaction2.response.edit_message(
                content=f"Selected attribute: **{attr}** ({attr_val}, MOD: {attr_mod})",
                view=self.parent_view
            )
        
        await interaction.response.send_message(
            "Select an attribute for your roll:",
            view=PaginatedSelectView(attr_options, on_attr_selected, interaction.user.id, prompt="Select an attribute:"),
            ephemeral=True
        )

class MGT2EBoonBaneButton(ui.Button):
    """Button that cycles through Boon/Bane states: None -> Boon -> Bane -> None"""
    def __init__(self, parent_view: MGT2ERollFormulaView):
        # Determine initial state and appearance
        current_state = parent_view.roll_formula_obj.boon_bane
        label, style = self._get_button_appearance(current_state)
        
        super().__init__(
            label=label,
            style=style,
            row=4
        )
        self.parent_view = parent_view
    
    def _get_button_appearance(self, boon_bane: BoonBane) -> tuple[str, discord.ButtonStyle]:
        """Get the appropriate label and style for the current boon/bane state"""
        if boon_bane.boons > 0:
            return "✨ Boon", discord.ButtonStyle.success
        elif boon_bane.banes > 0:
            return "⚡ Bane", discord.ButtonStyle.danger
        else:
            return "Boon/Bane", discord.ButtonStyle.secondary
    
    def _get_next_state(self, current_boon_bane: BoonBane) -> BoonBane:
        """Get the next state in the cycle: None -> Boon -> Bane -> None"""
        if not current_boon_bane.has_effect:
            # Currently none, next is boon
            return BoonBane(boons=1, banes=0)
        elif current_boon_bane.boons > 0:
            # Currently boon, next is bane
            return BoonBane(boons=0, banes=1)
        else:
            # Currently bane, next is none
            return BoonBane(boons=0, banes=0)
    
    def _get_status_message(self, boon_bane: BoonBane) -> str:
        """Get the status message for the current state"""
        if boon_bane.boons > 0:
            return "✅ Added boon - roll 3d6 and keep highest 2"
        elif boon_bane.banes > 0:
            return "✅ Added bane - roll 3d6 and keep lowest 2"
        else:
            return "✅ Cleared boons and banes - normal 2d6 roll"
    
    async def callback(self, interaction: discord.Interaction):
        # Get current state and calculate next state
        current_boon_bane = self.parent_view.roll_formula_obj.boon_bane
        next_boon_bane = self._get_next_state(current_boon_bane)
        
        # Update the roll formula
        self.parent_view.roll_formula_obj.boon_bane = next_boon_bane
        
        # Update button appearance
        new_label, new_style = self._get_button_appearance(next_boon_bane)
        self.label = new_label
        self.style = new_style
        
        # Get status message
        status_message = self._get_status_message(next_boon_bane)
        
        # Update the view
        await interaction.response.edit_message(
            content=status_message,
            view=self.parent_view
        )