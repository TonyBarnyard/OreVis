# OreVis robot

A small rounded-square robot that starts on wheels and evolves: tracks, then legs (Open Duck Mini), then an arm with a humanoid hand, then a voice. Every stage is built and tested in a digital twin before any parts are bought.

| Folder | What's in it |
|---|---|
| `sandbox/` | **The robot sandbox.** A 3D digital twin in the browser: pick parts, see if it will work, drive it, evolve it, talk to it, program it, and run missions. |
| `sim/` | **Physics bench (MuJoCo).** Runs the same designs through real rigid-body physics: speed, ramps, steps, standing, squatting and arm loads. |
| `plan/` | The original project plan and `robot_project_plan_v2.xlsx` with the review, the evolution roadmap, later-stage parts and test results. |
| `docs/PLAN_REVIEW.md` | What changed from the original plan, and why. |
| `sim/OPEN_DUCK.md` | How to get the walking version going with the open-source Open Duck Mini. |

## Try the sandbox

Open `sandbox/index.html` in a browser through any local web server:

```
cd sandbox && python3 -m http.server 8000
# then open http://localhost:8000
```

- **Evolution stage** buttons load the five planned designs. Change any part and the **Will it work?** panel recalculates mass, speed, battery life, cost and strength checks.
- Drive with **W A S D** or the arrow buttons. **G** grabs, **R** releases, **Q/E** tilt the camera.
- **Talk to the robot**: "put the red block in the red bin", "tidy up", "go to the green pad", "what can you do?". It only speaks once it has a voice (stage 5). Before that, it beeps.
- **Program** runs simple scripts: `forward 200`, `turn 90`, `look 20`, `pick red`, `place red`, `say hello`, `dance`, `tidy`.
- **Compare designs** saves designs side by side and exports a design file for the physics bench.

The sandbox uses deliberately simple physics. Anything that matters gets checked in `sim/`.

## Run the physics bench

```
pip install -r sim/requirements.txt
python sim/bench.py sim/designs/*.json          # all stage designs plus three "what if" designs
python sim/bench.py sim/designs/4_helper.json --view squat   # watch it in the MuJoCo viewer
```

Latest results (`sim/results.json`):

| Design | Result |
|---|---|
| 1 Hatchling (wheels) | 0.18 m/s, climbs 35° ramps, steps only 10 mm |
| 2 Explorer (tracks) | 0.23 m/s, 25° ramps, steps 15 mm |
| 3 Duckling (legs) | Stands and squats, knees peak at 32% of stall |
| 4 Helper (legs + arm) | Holds a block arm-out at 64% of shoulder stall, tilts 0.5° |
| Helper + Amazing Hand | **Tips over** (44°), shoulder at stall |
| Mini duck on SG90 servos | Knees hit **100%** of stall in a squat |

## Tests

```
node sandbox/test_sandbox.js        # browser smoke test: drive, refuse, tidy-up mission, tipping check (needs Playwright)
python sim/bench.py sim/designs/*.json
```
