# Pollen Robotics open-source code

Files in this folder come from [Pollen Robotics](https://www.pollen-robotics.com/) and keep their own licences.

| What | From | Commit | Licence |
|---|---|---|---|
| `AmazingHand/` (Python and Arduino examples, README) | [pollen-robotics/AmazingHand](https://github.com/pollen-robotics/AmazingHand) | `3e8241074df3436a3044ced4881e3bb2133aa725` | Apache 2.0 (software), CC BY 4.0 (mechanical design) |
| `AmazingHand/sim/` (MuJoCo model of the right and left hand, from `Demo/AHSimulation`) | same | same | Apache 2.0, CC BY 4.0 for the meshes |

Copied unchanged. The full CAD (STEP and STL print files, about 40 MB), the hand-tracking demo and Pollen's Reachy Mini SDK are not copied. Run `third_party/fetch_pollen.sh` to download them into `third_party/pollen/src/`, which git ignores.

Attribution for the mechanical design: "AmazingHand" by Pollen Robotics, licensed under CC BY 4.0.
