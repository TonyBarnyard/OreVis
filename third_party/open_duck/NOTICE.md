# Open Duck Mini files

| What | From | Commit | Licence |
|---|---|---|---|
| `BEST_WALK_ONNX_2.onnx`, the trained walking policy | [apirrone/Open_Duck_Mini](https://github.com/apirrone/Open_Duck_Mini) | `b23317a485b3cec7d8417f352478778b3475173c` | Apache 2.0 (`LICENSE`) |

Copied unchanged. Open Duck Mini is by Antoine Pirrone, Grégoire Passault and contributors.

`third_party/fetch_open_duck.sh` downloads the rest into `third_party/open_duck/src/`, which git ignores:

- **Open_Duck_Playground**: the MuJoCo model the policy was trained on. That repo has no licence file, so it is downloaded rather than copied here.
- **Open_Duck_Mini** (`mini_bdx/robots/open_duck_mini_v2` only): the full-detail 3D parts, Apache 2.0.

`sandbox/open_duck.json` and `sandbox/open_duck.b64.txt` are made by `sim/export_open_duck.py`. They hold the Open_Duck_Mini 3D parts and gait frames recorded from our own MuJoCo run of the policy. They contain nothing from Open_Duck_Playground except where the parts were placed while walking.
