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
  OreVisAR.Target.cs           Game build target (Android)
  OreVisAREditor.Target.cs     Editor build target
  OreVisAR/
    OreVisAR.Build.cs          Module dependencies
    OreVisAR.{h,cpp}           Primary game module
    OreVisARGameMode.{h,cpp}   Spawns initial objects around the player
    OreVisARPawn.{h,cpp}       Starts AR session, routes touch input
    ARPlaceableActor.{h,cpp}   Object that can be grabbed, moved, scaled
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
4. Create a Blueprint child of `AOreVisARPawn` (e.g. `BP_AROrePawn`) and
   assign `ARConfig`, `InputMapping`, and the three `IA_*` assets in its
   defaults.
5. Create a Blueprint child of `AOreVisARGameMode` (e.g. `BP_OreVisARGameMode`)
   and set:
   - `DefaultPawnClass = BP_AROrePawn`
   - `PlaceableClass   = AARPlaceableActor` (or a BP child with a custom mesh)
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
