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
| 1 | `GenericSheetEditView` | `core/generic_entities.py` | `GenericSheetEditViewV2` | **Done** | Low | V2 reference; now wired via `get_sheet_edit_view(guild_id=)` |
| 2 | `PaginatedSelectView` | `core/shared_views.py` | `PaginatedSelectViewV2` | **Done** | Medium | LayoutView selector added and wired into live V2 Fate/MGT2E sheet + roll flows |
| 3 | `SceneNotesEditView` | `core/shared_views.py` | `SceneNotesEditViewV2` | **Done** | Low | Self-contained scene notes LayoutView with modal return routing |
| 4 | `RequestRollView` | `core/shared_views.py` | `RequestRollViewV2` | **Done** | Medium | 1-week timeout LayoutView; `/roll request` now renders request text inside the view |
| 5 | `RollFormulaView` | `core/shared_views.py` | `RollFormulaViewV2` | **Done** | High | Components v2 base for interactive roll builders; shared modifier editing and finalize flow |

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
| 11 | `EditInventoryView` | `core/inventory_views.py` | `EditInventoryViewV2` | **Done** | Medium | LayoutView inventory root with paging, search, create-item, and done flow |
| 12 | `ItemManagementView` | `core/inventory_views.py` | `ItemManagementViewV2` | **Done** | Medium | LayoutView item actions with quantity/edit/transfer/remove routing |
| 13 | `FilteredInventoryView` | `core/inventory_views.py` | `FilteredInventoryViewV2` | **Done** | Medium | LayoutView search results with V2 item handoff and repeat-search support |
| 14 | `TransferItemView` | `core/inventory_views.py` | `TransferItemViewV2` | **Done** | Medium | LayoutView transfer workflow with destination selection and modal refresh support |

### Tier 4: Container/Entity Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 15 | `GenericContainerEditView` | `core/generic_entities.py` | `GenericContainerEditViewV2` | **Done** | Medium | V2 with self-contained content rendering; reveal/take/give flows now stay inside V2 |
| 16 | `ContainerTakeView` | `core/generic_entities.py` | `ContainerTakeViewV2` | **Done** | Low | 300s; migrated to LayoutView with inline selection summary and V2 return routing |
| 17 | `ContainerGiveView` | `core/generic_entities.py` | `ContainerGiveViewV2` | **Done** | Low | 300s; migrated to LayoutView with inline selection summary and V2 return routing |

### Tier 5: Roll Configuration Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 18 | `RollAndSumFormulaView` | `core/generic_roll_views.py` | `RollAndSumFormulaViewV2` | **Done** | Medium | LayoutView roll builder for roll-and-sum mechanics |
| 19 | `DicePoolFormulaView` | `core/generic_roll_views.py` | `DicePoolFormulaViewV2` | **Done** | Medium | LayoutView roll builder with add/clear dice and target controls |
| 20 | `CustomFormulaView` | `core/generic_roll_views.py` | `CustomFormulaViewV2` | **Done** | Low | LayoutView roll builder with custom formula modal integration |
| 21 | `CoreRollMechanicSelectView` | `core/generic_roll_mechanics.py` | `CoreRollMechanicSelectViewV2` | **Done** | Medium | Setup command now launches the V2 selection flow |
| 22 | `RollAndSumConfigView` | `core/generic_roll_mechanics.py` | `RollAndSumConfigViewV2` | **Done** | Medium | LayoutView config with modal refresh support |
| 23 | `DicePoolConfigView` | `core/generic_roll_mechanics.py` | `DicePoolConfigViewV2` | **Done** | Medium | LayoutView config with threshold/custom formula/exploding controls |
| 24 | `CustomConfigView` | `core/generic_roll_mechanics.py` | `CustomConfigViewV2` | **Done** | Low | LayoutView config with custom formula + exploding controls |
| 25 | `BasicConfigView` | `core/generic_roll_mechanics.py` | `BasicConfigViewV2` | **Done** | Low | LayoutView fallback confirm flow |

### Tier 6: Confirmation Dialogs (simple, low priority)

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 26 | `ConfirmDeleteView` | `commands/scene_commands.py` | `ConfirmDeleteViewV2` | **Done** | Low | Shared `ConfirmDialogV2` base; call site updated |
| 27 | `ConfirmRemoveAllLinksView` | `commands/link_commands.py` | `ConfirmRemoveAllLinksViewV2` | **Done** | Low | Shared `ConfirmDialogV2` base; call site updated |
| 28 | `ConfirmDeleteAllView` | `commands/entity_commands.py` | `ConfirmDeleteAllViewV2` | **Done** | Low | Shared `ConfirmDialogV2` base; call site updated |
| 29 | `ConfirmDeleteEntityView` | `commands/entity_commands.py` | `ConfirmDeleteEntityViewV2` | **Done** | Low | Shared `ConfirmDialogV2` base; call site updated |
| 30 | `ConfirmDeleteCharacterView` | `commands/character_commands.py` | `ConfirmDeleteCharacterViewV2` | **Done** | Low | Shared `ConfirmDialogV2` base; call site updated |

### Tier 7: Fate System Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 31 | `FateSceneView` | `rpg_systems/fate/fate_scene_views.py` | `FateSceneViewV2` | High | High | Persistent; registered in setup_hook; extends BasePinnableSceneView; aspects/zones/NPCs |
| 32 | `ZoneEditOptionsView` | `rpg_systems/fate/fate_scene_views.py` | `ZoneEditOptionsViewV2` | Low | Low | 300s; 2 buttons |
| 33 | `ManageNPCsView` (fate) | `rpg_systems/fate/fate_scene_views.py` | `FateManageNPCsViewV2` | Medium | Medium | 300s; select + done button |
| 34 | `FateSheetEditView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `FateSheetEditViewV2` | **Done** | High | Self-contained LayoutView rendering Fate sheet content with Components v2 |
| 35 | `EditAspectsView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditAspectsViewV2` | **Done** | High | Paginated aspect editor with V2 containers and modal return routing |
| 36 | `EditStressTracksView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditStressTracksViewV2` | **Done** | High | Track select + stress box toggles in LayoutView; modal return routing updated |
| 37 | `EditConsequencesView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditConsequencesViewV2` | **Done** | High | Consequence navigation/editing migrated to LayoutView |
| 38 | `EditStuntsView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `EditStuntsViewV2` | **Done** | Medium | Paginated stunt editor with V2 containers and actions |
| 39 | `SkillManagementView` | `rpg_systems/fate/fate_sheet_edit_views.py` | `SkillManagementViewV2` | **Done** | Medium | Skill management menu migrated; live V2 skill selection now uses `PaginatedSelectViewV2` |
| 40 | `CompelView` | `rpg_systems/fate/fate_compel_views.py` | `CompelViewV2` | **Done** | Medium | 1 week timeout LayoutView with conditional button rows and in-place status refresh |
| 41 | `FateRollFormulaView` | `rpg_systems/fate/fate_roll_views.py` | `FateRollFormulaViewV2` | **Done** | Medium | LayoutView roll builder with Fate skill selection routed through `PaginatedSelectViewV2` |

### Tier 8: MGT2E System Views

| # | V1 Class | File | V2 Class Name | Priority | Complexity | Notes |
|---|----------|------|---------------|----------|------------|-------|
| 42 | `MGT2ESceneView` | `rpg_systems/mgt2e/mgt2e_scene_views.py` | `MGT2ESceneViewV2` | High | High | Persistent; registered in setup_hook; extends BasePinnableSceneView |
| 43 | `ManageNPCsView` (mgt2e) | `rpg_systems/mgt2e/mgt2e_scene_views.py` | `MGT2EManageNPCsViewV2` | Medium | Medium | 300s; select + done |
| 44 | `MGT2ESheetEditView` | `rpg_systems/mgt2e/mgt2e_sheet_edit_views.py` | `MGT2ESheetEditViewV2` | **Done** | Medium | Self-contained LayoutView rendering Traveller sheet content; skill and inventory flows now stay in V2 |
| 45 | `MGT2ERollFormulaView` | `rpg_systems/mgt2e/mgt2e_roll_views.py` | `MGT2ERollFormulaViewV2` | **Done** | Medium | LayoutView roll builder with skill, attribute, and boon/bane controls via `PaginatedSelectViewV2` |

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
1. ~~Create a shared `ConfirmDialogV2` base class for all confirmation views (#26-30)~~ ✅ **Done** — `core/shared_views.py`
2. ~~Migrate confirmation dialogs (#26-30) using the shared base~~ ✅ **Done** — 5 V2 subclasses created alongside V1:
   - `ConfirmDeleteViewV2` in `commands/scene_commands.py`
   - `ConfirmDeleteAllViewV2` + `ConfirmDeleteEntityViewV2` in `commands/entity_commands.py`
   - `ConfirmRemoveAllLinksViewV2` in `commands/link_commands.py`
   - `ConfirmDeleteCharacterViewV2` in `commands/character_commands.py`
3. ~~Update call sites to use V2 confirmation dialogs~~ ✅ **Done** — all 5 call sites updated
4. ~~Migrate `GenericContainerEditView` (#15)~~ ✅ **Done** — `GenericContainerEditViewV2` created in `core/generic_entities.py` with self-contained content, status messages, and V1↔V2 transitions for Take/Give sub-views. `ContainerAccessModal` bug fixed (`container_id=` → `char_id=`) and updated for V2 support.
5. ~~Wire `GenericSheetEditViewV2` (#1) into actual use via `get_sheet_edit_view()`~~ ✅ **Done** — Added `guild_id: str = None` param to `get_sheet_edit_view()` across base class + all 7 overrides. When `guild_id` provided, returns V2 view with self-contained content. All 9 call sites updated with isinstance checks:
   - `commands/entity_commands.py` entity_view
   - `commands/character_commands.py` sheet
   - `commands/message_context_menu.py` view character sheet
   - `commands/user_context_menu.py` view character sheet
   - `core/shared_views.py` EditNameModal + EditNotesModal
   - `core/inventory_views.py` done_inventory + edit_item + _refresh_parent_view
   - Utility: `embed_to_text()` added to `core/shared_views.py` for Embed→markdown conversion

### Phase 2: Sheet Edit Views
4. ~~`FateSheetEditView` → `FateSheetEditViewV2` (#34)~~ ✅ **Done** — self-contained LayoutView rendering via `embed_to_text()`; wired through Fate character/extra `get_sheet_edit_view()` when `guild_id` is provided.
5. ~~`EditAspectsView`, `EditStressTracksView`, `EditConsequencesView`, `EditStuntsView`, `SkillManagementView` (#35-39)~~ ✅ **Done** — all five Fate subviews migrated to LayoutView with V2 containers/action rows; related modals updated to return to V2 views when invoked from the V2 flow.
6. ~~`MGT2ESheetEditView` → `MGT2ESheetEditViewV2` (#44)~~ ✅ **Done** — self-contained LayoutView added and wired through MGT2E `get_sheet_edit_view()`; attribute/skill modal returns updated for V2.

### Phase 3: Roll System
7. ~~`RollFormulaView` → `RollFormulaViewV2` (#5)~~ ✅ **Done** — added shared Components v2 roll-builder base in `core/shared_views.py`, plus V2-aware modifier modals and finalize flow.
8. ~~`RollAndSumFormulaView`, `DicePoolFormulaView`, `CustomFormulaView` (#18-20)~~ ✅ **Done** — generic roll builders migrated to LayoutView in `core/generic_roll_views.py`.
9. ~~`FateRollFormulaView` (#41), `MGT2ERollFormulaView` (#45)~~ ✅ **Done** — both system-specific roll builders migrated and wired into actual use; skill/attribute selection still bridges through `PaginatedSelectView` pending Phase 4.
10. ~~`CoreRollMechanicSelectView` and config views (#21-25)~~ ✅ **Done** — setup flow now uses `CoreRollMechanicSelectViewV2` and V2 config subviews with modal refresh support.

### Phase 4: Shared Views
11. ~~`PaginatedSelectView` (#2)~~ ✅ **Done** — added `PaginatedSelectViewV2` and wired it into active Fate/MGT2E V2 sheet + roll selection flows.
12. ~~`SceneNotesEditView` (#3), `RequestRollView` (#4)~~ ✅ **Done** — scene notes modal now returns `SceneNotesEditViewV2`; `/roll request` now uses `RequestRollViewV2`.
13. ~~Inventory views (#11-14)~~ ✅ **Done** — added `EditInventoryViewV2`, `ItemManagementViewV2`, `FilteredInventoryViewV2`, and `TransferItemViewV2`, plus modal refresh support.
14. ~~`CompelView` (#40)~~ ✅ **Done** — Fate compels now render through `CompelViewV2` with in-place LayoutView updates.

### Phase 5: Persistent Scene & Initiative Views (highest risk)
15. ~~`BasePinnableSceneView` → `BasePinnableSceneViewV2` (#6)~~ ✅ **Done** — LayoutView base added with self-contained container rendering, pinned-message refresh, and V1→V2 message editing.
16. ~~`GenericSceneView` (#7), `FateSceneView` (#31), `MGT2ESceneView` (#42)~~ ✅ **Done** — all three persistent scene views now have V2 implementations and are used by scene commands/factories.
17. ~~Scene sub-views: `ZoneEditOptionsView` (#32), `ManageNPCsView` (both) (#33, #43)~~ ✅ **Done** — Fate zone/NPC management and MGT2E NPC management now refresh through LayoutView subviews.
18. ~~`BasePinnedInitiativeView` → `BasePinnedInitiativeViewV2` (#8)~~ ✅ **Done** — added LayoutView initiative base with persistent message handling and current-turn notifications.
19. ~~`GenericInitiativeView` (#9), `PopcornInitiativeView` (#10)~~ ✅ **Done** — generic and popcorn initiative trackers now have V2 implementations, including restart-safe placeholder handling for popcorn selects.
20. ~~Update `main.py` `setup_hook` to register all V2 persistent views~~ ✅ **Done** — V2 scene and initiative persistent views are now registered alongside V1 for compatibility.

### Phase 6: Cleanup & Finalization
21. ~~Migrate all confirmation dialogs (#26-30) using the shared base~~ ✅ **Moved to Phase 1**
22. ~~Update all call sites to use V2 views by default~~ ✅ **Done** — direct command entry points, `get_sheet_edit_view()`, and factory-based view selection now prefer V2 when enabled.
23. ~~Add feature flag for V1 fallback~~ ✅ **Done** — added `core/view_config.py`; set `ROLEBYPOST_COMPONENTS_V2=false` (or `COMPONENTS_V2_ENABLED=false`) to force V1 fallback.
24. ~~Testing and deprecation of V1 classes~~ ✅ **Done** — updated files passed diagnostics, `python -m compileall .`, and a runtime smoke test for the feature flag. V1 classes remain available as compatibility fallback during rollout.

---

## Summary

| Category | Count |
|----------|-------|
| **Views to migrate** | 45 (45 done) |
| **Modals (no migration)** | 38 |
| **Standalone components (reuse as-is)** | ~30 buttons + 6 selects |
| **Persistent views (highest complexity)** | 5 (+ 2 abstract bases) |
| **New V2 classes to create** | 0 remaining |
| **Files affected** | 15+ |
| **Estimated phases** | 6 |
