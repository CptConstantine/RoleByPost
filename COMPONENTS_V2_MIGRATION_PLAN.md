# Components v2 Migration Plan

## Overview

Migrate all `discord.ui.View` subclasses to `discord.ui.LayoutView` equivalents using Components v2. New V2 classes are created alongside existing V1 classes for backward compatibility. Modals (`discord.ui.Modal`) are **not migrated** — they remain unchanged in Components v2.

**discord.py version:** 2.6.4  
**Reference implementation:** `GenericSheetEditViewV2` in `core/generic_entities.py`

---

## Key Migration Patterns

### Base Class Change
```python
# V1
class MyView(ui.View):
    ...

# V2
class MyViewV2(ui.LayoutView):
    ...
```

### Component Construction: Decorator → Imperative/Declarative

**Option A — Declarative (class-level ActionRow with decorators):**
```python
class MyViewV2(ui.LayoutView):
    row = ui.ActionRow()

    @row.button(label="Click Me", style=discord.ButtonStyle.primary, custom_id="click_me")
    async def click_me(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Clicked!")
```

**Option B — Imperative (build in `_build_layout()`):**
```python
class MyViewV2(ui.LayoutView):
    def __init__(self, ...):
        super().__init__(timeout=120)
        self._build_layout()

    def _build_layout(self):
        row = ui.ActionRow()
        btn = ui.Button(label="Click Me", custom_id="click_me")
        btn.callback = self.click_me
        row.add_item(btn)
        self.add_item(row)
```

**Recommendation:** Use **Option A** (declarative) for views with static layouts, **Option B** (imperative) for views with dynamic/conditional components.

### New Layout Components Available
- `ui.Container(*children, accent_colour=..., spoiler=...)` — Grouped sections with optional accent colour
- `ui.TextDisplay(content)` — Rich text (supports markdown, up to 4000 chars)
- `ui.Section(*children, accessory=...)` — Text + thumbnail/button pairing (up to 3 text displays)
- `ui.Separator(visible=True, spacing=SeparatorSpacing.small)` — Visual dividers
- `ui.Thumbnail(media)` — Section accessory images
- `ui.MediaGallery(*items)` — Image galleries
- `ui.File(media)` — File display

### Sending LayoutViews
**Critical constraint:** `LayoutView` messages **cannot** include `content=`, `embed=`, `embeds=`, `stickers=`, or `poll=`. All visual content must be inside the LayoutView using `TextDisplay`, `Container`, etc.

```python
# V1 — embed-based
await interaction.response.send_message(embed=embed, view=my_view, ephemeral=True)

# V2 — view IS the message
await interaction.response.send_message(view=my_layout_view, ephemeral=True)
```

When **editing** an existing message to switch from V1 → V2:
```python
await interaction.response.edit_message(
    content=None, embed=None, embeds=None, attachments=None,
    view=my_layout_view
)
```

### Persistent Views (timeout=None)
`LayoutView` supports persistent views the same way as `View`:
- All components must have explicit `custom_id`
- `timeout` must be `None`
- Must be registered via `bot.add_view()` in `setup_hook`
- Works with both `View` and `LayoutView`

### Call Site Updates
Every location that creates and sends a V1 View must be updated to optionally use the V2 version. This includes:
- Command handlers that `send_message(view=...)` 
- Callbacks that `edit_message(view=...)`
- Factory methods like `get_sheet_edit_view()`

**Strategy:** Introduce a feature flag or configuration to toggle V2 views, enabling gradual rollout.

---

## Migration Inventory

### Tier 1: Core Shared Views (highest impact, used everywhere)

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 1 | `GenericSheetEditView` | `core/generic_entities.py` | `GenericSheetEditViewV2` | **Done** | Low | Already exists as reference |
| 2 | `PaginatedSelectView` | `core/shared_views.py` | `PaginatedSelectViewV2` | High | Medium | Embed content → TextDisplay; PaginatedSelect component → ActionRow with Select |
| 3 | `SceneNotesEditView` | `core/shared_views.py` | `SceneNotesEditViewV2` | Medium | Low | Simple view with buttons |
| 4 | `RequestRollView` | `core/shared_views.py` | `RequestRollViewV2` | Medium | Medium | 1-week timeout, ephemeral=False, embed content → TextDisplay |
| 5 | `RollFormulaView` | `core/shared_views.py` | `RollFormulaViewV2` | High | High | Base class for all roll formula views; 24h timeout; dynamically adds buttons |

### Tier 2: Scene & Initiative Views (persistent, registered in setup_hook)

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 6 | `BasePinnableSceneView` | `core/scene_views.py` | `BasePinnableSceneViewV2` | High | High | ABC base; persistent; must coordinate with all subclasses |
| 7 | `GenericSceneView` | `core/scene_views.py` | `GenericSceneViewV2` | High | High | Persistent; registered in setup_hook; uses PlaceholderPersistentButton, SceneNotesButton |
| 8 | `BasePinnedInitiativeView` | `core/initiative_views.py` | `BasePinnedInitiativeViewV2` | High | High | ABC base; persistent; must coordinate with subclasses |
| 9 | `GenericInitiativeView` | `core/initiative_views.py` | `GenericInitiativeViewV2` | High | High | Persistent; uses StartInitiativeButton, EndTurnButton, SetOrderButton, FirstPickerSelect |
| 10 | `PopcornInitiativeView` | `core/initiative_views.py` | `PopcornInitiativeViewV2` | High | High | Persistent; uses PopcornNextSelect, EmptyPersistentSelect |

### Tier 3: Inventory Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 11 | `EditInventoryView` | `core/inventory_views.py` | `EditInventoryViewV2` | Medium | Medium | 120s; buttons for item management |
| 12 | `ItemManagementView` | `core/inventory_views.py` | `ItemManagementViewV2` | Medium | Medium | 120s; dynamic button construction |
| 13 | `FilteredInventoryView` | `core/inventory_views.py` | `FilteredInventoryViewV2` | Medium | Medium | 120s; filter + pagination |
| 14 | `TransferItemView` | `core/inventory_views.py` | `TransferItemViewV2` | Medium | Medium | 300s; transfer workflow |

### Tier 4: Container/Entity Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 15 | `GenericContainerEditView` | `core/generic_entities.py` | `GenericContainerEditViewV2` | Medium | Medium | 24h timeout; dynamic buttons from entity config |
| 16 | `ContainerTakeView` | `core/generic_entities.py` | `ContainerTakeViewV2` | Low | Low | 300s; simple select + buttons |
| 17 | `ContainerGiveView` | `core/generic_entities.py` | `ContainerGiveViewV2` | Low | Low | 300s; simple select + buttons |

### Tier 5: Roll Configuration Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 18 | `RollAndSumFormulaView` | `core/generic_roll_views.py` | `RollAndSumFormulaViewV2` | Medium | Medium | Extends RollFormulaView; 24h |
| 19 | `DicePoolFormulaView` | `core/generic_roll_views.py` | `DicePoolFormulaViewV2` | Medium | Medium | Extends RollFormulaView; 24h |
| 20 | `CustomFormulaView` | `core/generic_roll_views.py` | `CustomFormulaViewV2` | Medium | Low | Extends RollFormulaView; 24h |
| 21 | `CoreRollMechanicSelectView` | `core/generic_roll_mechanics.py` | `CoreRollMechanicSelectViewV2` | Medium | Medium | 300s; roll mechanic selection |
| 22 | `RollAndSumConfigView` | `core/generic_roll_mechanics.py` | `RollAndSumConfigViewV2` | Low | Medium | 300s; config sub-view |
| 23 | `DicePoolConfigView` | `core/generic_roll_mechanics.py` | `DicePoolConfigViewV2` | Low | Medium | 300s; config sub-view |
| 24 | `CustomConfigView` | `core/generic_roll_mechanics.py` | `CustomConfigViewV2` | Low | Low | 300s; simple config |
| 25 | `BasicConfigView` | `core/generic_roll_mechanics.py` | `BasicConfigViewV2` | Low | Low | 300s; simple config |

### Tier 6: Confirmation Dialogs (simple, low priority)

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 26 | `ConfirmDeleteView` | `commands/scene_commands.py` | `ConfirmDeleteViewV2` | Low | Low | 60s; 2 buttons (Delete + Cancel) |
| 27 | `ConfirmRemoveAllLinksView` | `commands/link_commands.py` | `ConfirmRemoveAllLinksViewV2` | Low | Low | 60s; 2 buttons |
| 28 | `ConfirmDeleteAllView` | `commands/entity_commands.py` | `ConfirmDeleteAllViewV2` | Low | Low | 60s; 2 buttons |
| 29 | `ConfirmDeleteEntityView` | `commands/entity_commands.py` | `ConfirmDeleteEntityViewV2` | Low | Low | 60s; 2 buttons |
| 30 | `ConfirmDeleteCharacterView` | `commands/character_commands.py` | `ConfirmDeleteCharacterViewV2` | Low | Low | 60s; 2 buttons |

### Tier 7: Fate System Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 31 | `FateSceneView` | `rpg_systems/fate/fate_scene_views.py` | `FateSceneViewV2` | High | High | Persistent; registered in setup_hook; extends BasePinnableSceneView; aspects/zones/NPCs |
| 32 | `ZoneEditOptionsView` | `rpg_systems/fate/fate_scene_views.py` | `ZoneEditOptionsViewV2` | Low | Low | 300s; 2 buttons |
| 33 | `ManageNPCsView` (fate) | `rpg_systems/fate/fate_scene_views.py` | `FateManageNPCsViewV2` | Medium | Medium | 300s; select + done button |
| 34 | `FateSheetEditView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `FateSheetEditViewV2` | High | High | 120s; 9 buttons across multiple rows |
| 35 | `EditAspectsView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditAspectsViewV2` | Medium | High | Dynamic paginated aspect editor; many conditional buttons |
| 36 | `EditStressTracksView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditStressTracksViewV2` | Medium | High | Dynamic stress box toggles; up to 5 boxes + management buttons |
| 37 | `EditConsequencesView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditConsequencesViewV2` | Medium | High | Dynamic consequence navigation + editing |
| 38 | `EditStuntsView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditStuntsViewV2` | Medium | Medium | Paginated stunt editor |
| 39 | `SkillManagementView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `SkillManagementViewV2` | Medium | Medium | 5 buttons for skill management |
| 40 | `CompelView` | `rpg_systems/fate/fate_compel_views.py` | `CompelViewV2` | Medium | Medium | 1 week timeout; conditional buttons based on compel type |
| 41 | `FateRollFormulaView` | `rpg_systems/fate/fate_roll_views.py` | `FateRollFormulaViewV2` | Medium | Medium | Extends RollFormulaView; adds skill selection |

### Tier 8: MGT2E System Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 42 | `MGT2ESceneView` | `rpg_systems/mgt2e/mgt2e_scene_views.py` | `MGT2ESceneViewV2` | High | High | Persistent; registered in setup_hook; extends BasePinnableSceneView |
| 43 | `ManageNPCsView` (mgt2e) | `rpg_systems/mgt2e/mgt2e_scene_views.py` | `MGT2EManageNPCsViewV2` | Medium | Medium | 300s; select + done |
| 44 | `MGT2ESheetEditView` | `rpg_systems/mgt2e/mgt2e_sheet_edit_views.py` | `MGT2ESheetEditViewV2` | High | Medium | 120s; 5 buttons |
| 45 | `MGT2ERollFormulaView` | `rpg_systems/mgt2e/mgt2e_roll_views.py` | `MGT2ERollFormulaViewV2` | Medium | Medium | Extends RollFormulaView; adds skill/attribute/boon-bane |

---

## Standalone Components to Migrate

These standalone `ui.Button` and `ui.Select` subclasses are used in persistent views. In V2, they can either:
- Remain as standalone classes (still work with `ActionRow.add_item()`)
- Be replaced by `@action_row.button()` decorators on the V2 view class

### Scene Buttons (persistent, custom_id required)
| Component | File | Approach |
|-----------|------|----------|
| `PlaceholderPersistentButton` | `core/scene_views.py` | Keep as-is, add to ActionRow |
| `SceneNotesButton` | `core/scene_views.py` | Keep as-is, add to ActionRow |
| `EditGameAspectsButton` | `rpg_systems/fate/fate_scene_views.py` | Keep as-is, add to ActionRow |
| `EditSceneAspectsButton` | `rpg_systems/fate/fate_scene_views.py` | Keep as-is, add to ActionRow |
| `EditZonesButton` | `rpg_systems/fate/fate_scene_views.py` | Keep as-is, add to ActionRow |
| `ManageNPCsButton` (fate) | `rpg_systems/fate/fate_scene_views.py` | Keep as-is, add to ActionRow |
| `EditEnvironmentButton` | `rpg_systems/mgt2e/mgt2e_scene_views.py` | Keep as-is, add to ActionRow |
| `ManageNPCsButton` (mgt2e) | `rpg_systems/mgt2e/mgt2e_scene_views.py` | Keep as-is, add to ActionRow |

### Initiative Components (persistent)
| Component | File | Approach |
|-----------|------|----------|
| `StartInitiativeButton` | `core/initiative_views.py` | Keep as-is, add to ActionRow |
| `EndTurnButton` | `core/initiative_views.py` | Keep as-is, add to ActionRow |
| `SetOrderButton` | `core/initiative_views.py` | Keep as-is, add to ActionRow |
| `FirstPickerSelect` | `core/initiative_views.py` | Keep as-is, add to ActionRow |
| `PopcornNextSelect` | `core/initiative_views.py` | Keep as-is, add to ActionRow |
| `EmptyPersistentSelect` | `core/initiative_views.py` | Keep as-is, add to ActionRow |

### Other Standalone Components
| Component | File | Approach |
|-----------|------|----------|
| `PaginatedSelect` | `core/shared_views.py` | Keep as-is, add to ActionRow |
| `FinalizeRollButton` | `core/shared_views.py` | Keep as-is, add to ActionRow |
| `ManageNPCsSelect` (fate) | `rpg_systems/fate/fate_scene_views.py` | Keep as-is, add to ActionRow |
| `DoneButton` (fate) | `rpg_systems/fate/fate_scene_views.py` | Keep as-is, add to ActionRow |
| `ManageNPCsSelect` (mgt2e) | `rpg_systems/mgt2e/mgt2e_scene_views.py` | Keep as-is, add to ActionRow |
| `DoneButton` (mgt2e) | `rpg_systems/mgt2e/mgt2e_scene_views.py` | Keep as-is, add to ActionRow |
| `FateSelectSkillButton` | `rpg_systems/fate/fate_roll_views.py` | Keep as-is, add to ActionRow |
| `MGT2ESelectSkillButton` | `rpg_systems/mgt2e/mgt2e_roll_views.py` | Keep as-is, add to ActionRow |
| `MGT2ESelectAttributeButton` | `rpg_systems/mgt2e/mgt2e_roll_views.py` | Keep as-is, add to ActionRow |
| `MGT2EBoonBaneButton` | `rpg_systems/mgt2e/mgt2e_roll_views.py` | Keep as-is, add to ActionRow |
| Compel buttons (5 classes) | `rpg_systems/fate/fate_compel_views.py` | Keep as-is, add to ActionRow |

---

## Modals — NO MIGRATION NEEDED

All 38 Modal classes remain unchanged. Modals use `ui.Modal` which is unaffected by Components v2. The only new Modal feature is `ui.Label` (wraps `TextInput` with label/description), which is optional.

| Count | File |
|-------|------|
| 5 | `core/shared_views.py` |
| 1 | `core/scene_views.py` |
| 1 | `core/initiative_views.py` |
| 4 | `core/inventory_views.py` |
| 3 | `core/generic_entities.py` |
| 3 | `core/generic_roll_views.py` |
| 5 | `core/generic_roll_mechanics.py` |
| 1 | `commands/message_context_menu.py` |
| 4 | `rpg_systems/fate/fate_scene_views.py` |
| 13 | `rpg_systems/fate/fate_sheet_edit_views.py` |
| 1 | `rpg_systems/fate/fate_compel_views.py` |
| 1 | `rpg_systems/mgt2e/mgt2e_scene_views.py` |
| 3 | `rpg_systems/mgt2e/mgt2e_sheet_edit_views.py` |

---

## Call Site Changes Required

Every place that sends or edits a message with a V1 View must be updated. Key patterns:

### Pattern 1: send_message with embed + view
```python
# Before
await interaction.response.send_message(embed=embed, view=my_view, ephemeral=True)

# After (V2) — embed content moves into LayoutView as TextDisplay/Container
await interaction.response.send_message(view=my_layout_view, ephemeral=True)
```

### Pattern 2: edit_message switching views
```python
# Before  
await interaction.response.edit_message(content="text", view=new_view)

# After (V2) — must clear content/embeds when switching to LayoutView
await interaction.response.edit_message(content=None, embed=None, view=new_layout_view)
```

### Pattern 3: Persistent view registration in main.py setup_hook
```python
# Before
bot.add_view(GenericSceneView())

# After — register both V1 and V2 for backward compatibility
bot.add_view(GenericSceneView())    # handles existing V1 messages
bot.add_view(GenericSceneViewV2())  # handles new V2 messages
```

### Key Call Sites to Update
| Location | Current Pattern | Change Needed |
|----------|----------------|---------------|
| `main.py` `setup_hook` | Registers 5 persistent views | Add V2 persistent view registrations |
| `core/generic_entities.py` `get_sheet_edit_view()` | Returns V1 view | Return V2 view (or add V2 factory) |
| `commands/scene_commands.py` | Creates scene views with embeds | Embed → TextDisplay in V2 view |
| `commands/initiative_commands.py` | Creates initiative views with embeds | Embed → TextDisplay in V2 view |
| `commands/roll_commands.py` | Creates roll formula views | Update to V2 formula views |
| `commands/entity_commands.py` | Creates entity edit views | Update to V2 entity views |
| `commands/character_commands.py` | Creates sheet edit views | Update to V2 sheet views |
| All system-specific commands | Create system-specific views | Update to V2 system views |

---

## V2 Enhancement Opportunities

With Components v2, several UX improvements become possible:

1. **Accent colours on Containers** — Use system-specific colours (e.g., Fate = blue, MGT2E = green) for visual distinction
2. **TextDisplay for inline text** — Replace embed fields with richer, more flexible text
3. **Sections with Thumbnails** — Character sheets can show character images alongside stats
4. **Separators** — Clean visual separation between logical groups (e.g., stats vs actions)
5. **Containers for grouping** — Group related content with optional spoiler tags (e.g., GM-only notes)
6. **4000-char limit per TextDisplay** — More text capacity than embed fields (1024 per field)

---

## Implementation Order (Recommended)

### Phase 1: Foundation & Simple Views
1. Create a shared `ConfirmDialogV2` base class for all confirmation views (#26-30)
2. Migrate `GenericContainerEditView` (#15), `ContainerTakeView` (#16), `ContainerGiveView` (#17)
3. Wire `GenericSheetEditViewV2` (#1) into actual use via `get_sheet_edit_view()`

### Phase 2: Sheet Edit Views
4. `FateSheetEditView` → `FateSheetEditViewV2` (#34)
5. `EditAspectsView`, `EditStressTracksView`, `EditConsequencesView`, `EditStuntsView`, `SkillManagementView` (#35-39)
6. `MGT2ESheetEditView` → `MGT2ESheetEditViewV2` (#44)

### Phase 3: Roll System
7. `RollFormulaView` → `RollFormulaViewV2` (#5) — base class first
8. `RollAndSumFormulaView`, `DicePoolFormulaView`, `CustomFormulaView` (#18-20)
9. `FateRollFormulaView` (#41), `MGT2ERollFormulaView` (#45)
10. `CoreRollMechanicSelectView` and config views (#21-25)

### Phase 4: Shared Views
11. `PaginatedSelectView` (#2)
12. `SceneNotesEditView` (#3), `RequestRollView` (#4)
13. Inventory views (#11-14)
14. `CompelView` (#40)

### Phase 5: Persistent Scene & Initiative Views (highest risk)
15. `BasePinnableSceneView` → `BasePinnableSceneViewV2` (#6) — abstract base first
16. `GenericSceneView` (#7), `FateSceneView` (#31), `MGT2ESceneView` (#42)
17. Scene sub-views: `ZoneEditOptionsView` (#32), `ManageNPCsView` (both) (#33, #43)
18. `BasePinnedInitiativeView` → `BasePinnedInitiativeViewV2` (#8)
19. `GenericInitiativeView` (#9), `PopcornInitiativeView` (#10)
20. Update `main.py` `setup_hook` to register all V2 persistent views

### Phase 6: Confirmation Dialogs & Cleanup
21. Migrate all confirmation dialogs (#26-30) using the shared base
22. Update all call sites to use V2 views by default
23. Add feature flag for V1 fallback
24. Testing and deprecation of V1 classes

---

## Summary

| Category | Count |
|----------|-------|
| **Views to migrate** | 45 (1 already done) |
| **Modals (no migration)** | 38 |
| **Standalone components (reuse as-is)** | ~30 buttons + 6 selects |
| **Persistent views (highest complexity)** | 5 (+ 2 abstract bases) |
| **New V2 classes to create** | 44 |
| **Files affected** | 15+ |
| **Estimated phases** | 6 |
