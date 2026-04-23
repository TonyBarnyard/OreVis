# OreVis AR

Simple Unreal Engine 5 AR app that spawns 3D objects within a 10 m radius of
the user and lets them pinch-to-select, drag-to-move, and pinch-to-scale each
object.

Target hardware:

- **Phone:** Samsung Galaxy S24 (ARCore compute + touchscreen input)
- **Display:** XREAL Air / Air 2 / Light glasses, connected to the S24 via
  USB-C DisplayPort Alt Mode. Head-pose comes from the glasses' IMU via OpenXR;
  environment tracking comes from the phone's rear camera via ARCore.

## Project layout

```
OreVisAR.uproject              Project descriptor, plugin set
Config/
  DefaultEngine.ini            Renderer, Android, ARSession settings
  DefaultGame.ini              Project name + AR tunables
  DefaultInput.ini             Touch + Enhanced Input defaults
Source/
  OreVisAR.Target.cs              Game build target (Android)
  OreVisAREditor.Target.cs        Editor build target
  OreVisAR/
    OreVisAR.Build.cs             Module dependencies
    OreVisAR.{h,cpp}              Primary game module
    OreVisARGameMode.{h,cpp}      Spawns objects, creates HUD widgets
    OreVisARPawn.{h,cpp}          Starts AR session, drives stage transitions
    ARPlaceableActor.{h,cpp}      Object that can be grabbed, moved, scaled
    OreVisStartupSubsystem.{h,cpp} 0–100% startup progress tracker
    StartupTachoWidget.{h,cpp}    Sample HUD tacho bound to the subsystem
    ARSpawnButtonWidget.{h,cpp}   Sample tap-to-spawn HUD button
```

## How the interaction works

The S24's touchscreen is the input device (XREAL Air/Light has no hand
tracking). Enhanced Input feeds three actions into `AOreVisARPawn`:

| Action        | Gesture                    | Effect                                                   |
| ------------- | -------------------------- | -------------------------------------------------------- |
| `IA_Touch`    | 1 finger down / up         | Ray-trace from the touch point; grab/release a placeable |
| `IA_TouchMove`| 1 finger drag              | Moves the grabbed object along the view ray             |
| `IA_Pinch`    | 2 finger pinch             | Uniformly scales the grabbed object (clamped)           |

Every placeable is kept within `MaxPlacementRadiusCm` (default **1000 cm = 10 m**)
of the pawn, both during drag (`MoveGrabbedAlongView` deprojects at grab-time
distance and then clamps) and on Tick (`ClampToPlacementRadius`).

## Startup progress (0 → 100%) and sample HUD

`UOreVisStartupSubsystem` (a `UGameInstanceSubsystem`) drives a single float
that ticks from 0 to 1 as the AR app boots. Every stage change fires
`OnProgressChanged(Progress01, Stage)`:

| Stage                | Percent | Trigger                                                        |
| -------------------- | ------- | -------------------------------------------------------------- |
| `NotStarted`         | 0%      | (default)                                                      |
| `LoadingAssets`      | 10%     | `UOreVisStartupSubsystem::Initialize` runs                      |
| `StartingARSession`  | 25%     | pawn `BeginPlay` just before `StartARSession`                  |
| `WaitingForTracking` | 50%     | pawn `BeginPlay` just after `StartARSession`                   |
| `ScatteringObjects`  | 75%     | pawn `Tick` detects `EARSessionStatus::Running`                |
| `Ready`              | 100%    | initial objects scattered and the session is interactive       |

### Sample widgets

Two UMG base classes ship in the module. Create BP children in-editor for the
visuals — the native hooks auto-wire themselves.

**`UStartupTachoWidget`** — bind any of these optional sub-widgets in the BP:

| Named widget     | Type          | Behavior                                                   |
| ---------------- | ------------- | ---------------------------------------------------------- |
| `ProgressBar`    | `UProgressBar`| Linear fill auto-driven from 0..1                          |
| `StageLabel`     | `UTextBlock`  | "Waiting For Tracking", etc.                               |
| `PercentLabel`   | `UTextBlock`  | "42%"                                                      |
| `TachoImage`     | `UImage`      | The dynamic material's `Progress` scalar is driven         |

For a true radial tachometer, put a `UImage` named `TachoImage` with a
material that reads a `Progress` scalar parameter (use `M_RadialGauge` —
a simple material that clips an annular arc by `Progress` works well). You
can also override `OnTachoProgressUpdated(Progress, Stage)` in the BP to
drive custom widget animations.

`bHideWhenReady` (default true) collapses the widget `HideDelaySeconds`
after hitting 100%.

Place two instances to get *two* tachos — e.g. a big center dial plus a
smaller corner readout — by assigning both `StartupTachoWidgetClass` and
`SecondaryTachoWidgetClass` on the game mode.

**`UARSpawnButtonWidget`** — tap to drop a new placeable `SpawnDistanceCm`
in front of the camera. Bind a `UButton` named `SpawnButton` in the BP.

Wire the widget classes on your `BP_OreVisARGameMode` defaults:

- `StartupTachoWidgetClass  = WBP_StartupTacho`
- `SecondaryTachoWidgetClass = WBP_CornerTacho` (optional)
- `SpawnButtonWidgetClass   = WBP_ARSpawnButton`

## First-time setup in the Unreal editor

The C++ code is complete, but a few assets must be created in-editor (they are
binary `.uasset` files and don't live in git):

1. Create `/Game/Maps/ARWorld` — an empty map with no skylight/directional
   light (AR uses a transparent background).
2. Create a `UARSessionConfig` asset under `/Game/AR/ARSession_Default`.
   Open it and set:
   - `WorldAlignment = Gravity`
   - `SessionType = World`
   - `PlaneDetectionMode = Horizontal | Vertical`
3. Create Enhanced Input assets under `/Game/Input/`:
   - `IA_Touch` (Digital / bool)
   - `IA_TouchMove` (Axis2D)
   - `IA_Pinch` (Axis1D)
   - `IMC_Default` — map `Touch1` to `IA_Touch`, add a `Touch` → `Axis2D`
     modifier for `IA_TouchMove`, and bind a pinch gesture (or a two-finger
     vertical swipe modifier) to `IA_Pinch`.
3a. Create HUD widgets under `/Game/UI/`:
   - `WBP_StartupTacho` — BP child of `UStartupTachoWidget`. Add a
     `ProgressBar` named `ProgressBar`, a `TextBlock` named `PercentLabel`,
     optionally a `TextBlock` named `StageLabel`, and optionally an `Image`
     named `TachoImage` backed by a radial-fill material.
   - `WBP_ARSpawnButton` — BP child of `UARSpawnButtonWidget`. Add a `Button`
     named `SpawnButton` plus whatever icon/label you want inside it.
4. Create a Blueprint child of `AOreVisARPawn` (e.g. `BP_AROrePawn`) and
   assign `ARConfig`, `InputMapping`, and the three `IA_*` assets in its
   defaults.
5. Create a Blueprint child of `AOreVisARGameMode` (e.g. `BP_OreVisARGameMode`)
   and set:
   - `DefaultPawnClass          = BP_AROrePawn`
   - `PlaceableClass            = AARPlaceableActor` (or a BP child with a custom mesh)
   - `StartupTachoWidgetClass   = WBP_StartupTacho`
   - `SpawnButtonWidgetClass    = WBP_ARSpawnButton`
   - `SecondaryTachoWidgetClass = WBP_CornerTacho` (optional)
6. In **Project Settings → Maps & Modes**, set `GlobalDefaultGameMode =
   BP_OreVisARGameMode`.

## Building for Android (S24 + XREAL)

1. Install the Unreal Android toolchain (`AndroidWorks`/Android Studio SDK
   + NDK r25b, per `Engine/Extras/Android/SetupAndroid.*`).
2. **Project Settings → Platforms → Android**:
   - Minimum SDK 28, Target SDK 33
   - Support Vulkan: **on**, Support OpenGL ES3.1: **off**
   - Package game data inside APK: on
   - Enable Google Play Support: **off** (we don't ship via Play Store for this)
3. **Project Settings → Plugins**:
   - `Google ARCore`: enabled (Android only)
   - `OpenXR` + `XR Base` + `XR Visualization`: enabled (these pick up the
     XREAL runtime once the XREAL Unreal SDK is dropped into
     `Plugins/NRSDK` — download from XREAL's developer portal and restart
     the editor).
4. Package: **Platforms → Android (ASTC) → Package Project**.
5. Connect the S24 in USB debugging mode, run
   `adb install -r <packaged>.apk`.
6. Plug the XREAL glasses into the S24 over USB-C. Launch the app; the phone
   drives ARCore in the background while the output streams to the glasses.

## Tuning the 10 m radius

All placement limits funnel through a single config key:

```
; Config/DefaultGame.ini
[/Script/OreVisAR.OreVisARGameMode]
MaxPlacementRadiusCm=1000.0
InitialObjectCount=3
```

The game mode copies this to the pawn on `StartPlay`, so both spawn scatter
and runtime drag-clamping stay in lockstep.
