"""
setup_orevis_assets.py  —  one-shot editor-asset bootstrapper for OreVis AR.

Run INSIDE the Unreal Editor:
    Tools → Execute Python Script → pick this file
or from the Output Log python prompt:
    py <project>/Scripts/setup_orevis_assets.py

It creates (idempotently — safe to re-run):

    /Game/Maps/ARWorld                     blank persistent level
    /Game/AR/ARSession_Default             UARSessionConfig (gravity, planes)
    /Game/Input/IA_Touch                   Digital / bool
    /Game/Input/IA_TouchMove               Axis2D
    /Game/Input/IA_Pinch                   Axis1D
    /Game/Input/IMC_Default                maps Touch1→IA_Touch
    /Game/UI/WBP_StartupTacho              WidgetBP : UStartupTachoWidget
    /Game/UI/WBP_ARSpawnButton             WidgetBP : UARSpawnButtonWidget
    /Game/Blueprints/BP_AROrePawn          BP : AOreVisARPawn
    /Game/Blueprints/BP_OreVisARGameMode   BP : AOreVisARGameMode

Then sets Project Settings so the map + game mode are default.

Prerequisites:
    - OreVisAR.uproject opened once so the C++ module compiled.
    - Plugins enabled: Python Editor Script Plugin, Editor Scripting
      Utilities, Enhanced Input, Augmented Reality, Google ARCore
      (Android), OpenXR.

After running, open WBP_StartupTacho / WBP_ARSpawnButton once and drop in
the named sub-widgets (ProgressBar/TextBlock/Button) listed in the README
— that step is manual because UMG widget-tree layout via Python is
unreliable across UE versions.
"""

from __future__ import annotations

import unreal

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

EAL = unreal.EditorAssetLibrary
ATOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg: str) -> None:
    unreal.log(f"[OreVis setup] {msg}")


def warn(msg: str) -> None:
    unreal.log_warning(f"[OreVis setup] {msg}")


def ensure_dir(path: str) -> None:
    if not EAL.does_directory_exist(path):
        EAL.make_directory(path)
        log(f"mkdir {path}")


def load_native_class(class_path: str):
    """Load a UClass by full path, e.g. '/Script/OreVisAR.OreVisARPawn'."""
    cls = unreal.load_class(None, class_path)
    if cls is None:
        # Try loading the Class object directly (works for some UE versions).
        obj = unreal.load_object(None, class_path + "_C") or unreal.load_object(None, class_path)
        cls = obj if isinstance(obj, unreal.Class) else cls
    return cls


def asset_exists(pkg: str, name: str) -> bool:
    return EAL.does_asset_exist(f"{pkg}/{name}")


def load_asset(pkg: str, name: str):
    return EAL.load_asset(f"{pkg}/{name}")


def save(asset) -> None:
    EAL.save_loaded_asset(asset, False)


def create_asset(pkg: str, name: str, asset_class, factory):
    if asset_exists(pkg, name):
        log(f"exists: {pkg}/{name} — loading existing")
        return load_asset(pkg, name)
    asset = ATOOLS.create_asset(name, pkg, asset_class, factory)
    if asset is None:
        warn(f"failed to create {pkg}/{name}")
    else:
        log(f"created: {pkg}/{name}")
    return asset


def try_set(obj, prop_name: str, value) -> bool:
    """set_editor_property but swallow the error if the property isn't exposed
    in this UE version — lets the script keep going."""
    try:
        obj.set_editor_property(prop_name, value)
        return True
    except Exception as e:  # noqa: BLE001
        warn(f"{obj.get_name()}.{prop_name} = {value!r} failed: {e}")
        return False


# ---------------------------------------------------------------------------
# 1. Folders
# ---------------------------------------------------------------------------

def make_folders() -> None:
    for p in (
        "/Game/Maps",
        "/Game/AR",
        "/Game/Input",
        "/Game/UI",
        "/Game/Blueprints",
    ):
        ensure_dir(p)


# ---------------------------------------------------------------------------
# 2. Blank map
# ---------------------------------------------------------------------------

def make_map() -> None:
    map_path = "/Game/Maps/ARWorld"
    if EAL.does_asset_exist(map_path):
        log(f"exists: {map_path}")
        return
    try:
        # UE 5.1+
        unreal.EditorLevelLibrary.new_level(map_path)
        log(f"created: {map_path}")
    except Exception as e:  # noqa: BLE001
        warn(f"new_level failed: {e}  — create /Game/Maps/ARWorld manually")


# ---------------------------------------------------------------------------
# 3. AR Session Config
# ---------------------------------------------------------------------------

def make_ar_session_config():
    ar_cfg = create_asset("/Game/AR", "ARSession_Default",
                          unreal.ARSessionConfig, None)
    if ar_cfg is None:
        return None

    # Property name varies slightly across UE versions; try both camelCase
    # and snake_case. UE Python prefers snake_case.
    try_set(ar_cfg, "world_alignment", unreal.ARWorldAlignment.GRAVITY)
    try_set(ar_cfg, "session_type", unreal.ARSessionType.WORLD)
    try_set(ar_cfg, "horizontal_plane_detection", True)
    try_set(ar_cfg, "vertical_plane_detection", True)
    try_set(ar_cfg, "enable_auto_focus", True)
    try_set(ar_cfg, "light_estimation_mode", unreal.ARLightEstimationMode.AMBIENT_LIGHT_ESTIMATION)
    save(ar_cfg)
    return ar_cfg


# ---------------------------------------------------------------------------
# 4. Enhanced Input
# ---------------------------------------------------------------------------

def make_input_action(name: str, value_type):
    # UE 5.x exposes unreal.InputAction directly; factories live under
    # unreal.InputActionFactory in engine-provided plugins. Fall back to
    # raw create_asset with class if the factory symbol is missing.
    factory = None
    try:
        factory = unreal.InputActionFactory()
    except Exception:
        factory = None

    ia = create_asset("/Game/Input", name, unreal.InputAction, factory)
    if ia is None:
        return None
    try_set(ia, "value_type", value_type)
    save(ia)
    return ia


def make_input_mapping_context(ia_touch):
    factory = None
    try:
        factory = unreal.InputMappingContextFactory()
    except Exception:
        factory = None

    imc = create_asset("/Game/Input", "IMC_Default",
                       unreal.InputMappingContext, factory)
    if imc is None:
        return None

    # Map Touch1 → IA_Touch. The IMC API varies by UE version; wrap in try.
    try:
        imc.map_key(ia_touch, unreal.InputKey(key_name="Touch1"))
        log("IMC_Default: bound Touch1 → IA_Touch")
    except Exception as e:  # noqa: BLE001
        warn(f"map_key failed ({e}); bind Touch1→IA_Touch manually in the IMC.")
    save(imc)
    return imc


def make_enhanced_input():
    ia_touch = make_input_action("IA_Touch", unreal.InputActionValueType.BOOLEAN)
    ia_move = make_input_action("IA_TouchMove", unreal.InputActionValueType.AXIS2_D)
    ia_pinch = make_input_action("IA_Pinch", unreal.InputActionValueType.AXIS1_D)
    imc = make_input_mapping_context(ia_touch) if ia_touch else None
    return ia_touch, ia_move, ia_pinch, imc


# ---------------------------------------------------------------------------
# 5. Blueprints
# ---------------------------------------------------------------------------

def make_blueprint_child(pkg: str, name: str, parent_class_path: str):
    parent = load_native_class(parent_class_path)
    if parent is None:
        warn(f"parent class not found: {parent_class_path} — is the module "
             "compiled? Open the .uproject once and let UE build.")
        return None

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", parent)

    bp = create_asset(pkg, name, None, factory)
    if bp is None:
        return None
    save(bp)
    return bp


def make_widget_blueprint_child(pkg: str, name: str, parent_class_path: str):
    parent = load_native_class(parent_class_path)
    if parent is None:
        warn(f"parent class not found: {parent_class_path}")
        return None

    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property("parent_class", parent)

    wbp = create_asset(pkg, name, None, factory)
    if wbp is None:
        return None
    save(wbp)
    return wbp


def assign_bp_defaults(bp, prop_name: str, value) -> bool:
    """Set a default on a Blueprint's CDO, then recompile."""
    if bp is None or value is None:
        return False
    try:
        cdo = unreal.get_default_object(bp.generated_class())
        cdo.set_editor_property(prop_name, value)
        # Force the BP to recompile so the change is baked into the template.
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        log(f"{bp.get_name()}.{prop_name} = {value.get_name() if hasattr(value, 'get_name') else value}")
        return True
    except Exception as e:  # noqa: BLE001
        warn(f"assign {bp}.{prop_name}: {e}")
        return False


# ---------------------------------------------------------------------------
# 6. Project Settings: default map + global game mode
# ---------------------------------------------------------------------------

def set_project_defaults(bp_game_mode) -> None:
    settings = unreal.get_default_object(unreal.GameMapsSettings)

    # Default map
    try:
        settings.set_editor_property("game_default_map", unreal.SoftObjectPath("/Game/Maps/ARWorld.ARWorld"))
        settings.set_editor_property("editor_startup_map", unreal.SoftObjectPath("/Game/Maps/ARWorld.ARWorld"))
        log("ProjectSettings: default map = /Game/Maps/ARWorld")
    except Exception as e:  # noqa: BLE001
        warn(f"set default map: {e}")

    # Global default game mode (SoftClassPath to the BP generated class)
    if bp_game_mode is not None:
        try:
            gm_path = unreal.SoftClassPath(bp_game_mode.generated_class().get_path_name())
            settings.set_editor_property("global_default_game_mode", gm_path)
            log("ProjectSettings: global default game mode = BP_OreVisARGameMode")
        except Exception as e:  # noqa: BLE001
            warn(f"set global game mode: {e}")

    try:
        settings.save_config()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log("starting setup…")

    make_folders()
    make_map()
    ar_cfg = make_ar_session_config()
    ia_touch, ia_move, ia_pinch, imc = make_enhanced_input()

    bp_pawn = make_blueprint_child(
        "/Game/Blueprints", "BP_AROrePawn",
        "/Script/OreVisAR.OreVisARPawn")
    bp_gm = make_blueprint_child(
        "/Game/Blueprints", "BP_OreVisARGameMode",
        "/Script/OreVisAR.OreVisARGameMode")

    wbp_tacho = make_widget_blueprint_child(
        "/Game/UI", "WBP_StartupTacho",
        "/Script/OreVisAR.StartupTachoWidget")
    wbp_spawn = make_widget_blueprint_child(
        "/Game/UI", "WBP_ARSpawnButton",
        "/Script/OreVisAR.ARSpawnButtonWidget")

    # Wire the pawn defaults
    assign_bp_defaults(bp_pawn, "ARConfig", ar_cfg)
    assign_bp_defaults(bp_pawn, "InputMapping", imc)
    assign_bp_defaults(bp_pawn, "IA_Touch", ia_touch)
    assign_bp_defaults(bp_pawn, "IA_TouchMove", ia_move)
    assign_bp_defaults(bp_pawn, "IA_Pinch", ia_pinch)

    # Wire the game-mode defaults
    if bp_pawn is not None:
        assign_bp_defaults(bp_gm, "DefaultPawnClass", bp_pawn.generated_class())
    if wbp_tacho is not None:
        assign_bp_defaults(bp_gm, "StartupTachoWidgetClass", wbp_tacho.generated_class())
    if wbp_spawn is not None:
        assign_bp_defaults(bp_gm, "SpawnButtonWidgetClass", wbp_spawn.generated_class())

    set_project_defaults(bp_gm)

    log("done.")
    log("Manual follow-ups:")
    log("  1. Open WBP_StartupTacho and add:")
    log("       ProgressBar   (name it 'ProgressBar')")
    log("       TextBlock     (name it 'PercentLabel')")
    log("       TextBlock     (name it 'StageLabel')        [optional]")
    log("       Image         (name it 'TachoImage')        [optional]")
    log("  2. Open WBP_ARSpawnButton and add:")
    log("       Button        (name it 'SpawnButton')")
    log("     Put whatever icon/text you want inside the button.")
    log("  3. Open IMC_Default and bind:")
    log("       IA_TouchMove  ← Touch1  + 'Swizzle Input Axis Values' modifier (2D)")
    log("       IA_Pinch      ← Gesture / two-finger pinch if available, or")
    log("                       Touch2 + a custom curve.")
    log("  4. Package → Android (ASTC) and install on the S24.")


if __name__ == "__main__":
    main()
