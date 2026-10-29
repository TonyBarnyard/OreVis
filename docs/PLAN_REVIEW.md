# OreVis robot: plan review and adaptations

This reviews the original plan (`plan/robot_project_plan.xlsx`, the rounded-square Pico W robot from the concept sheet) and adapts it for three new goals: a walking version built on Open Duck Mini, a humanoid hand that can move objects, and a robot that evolves in stages until it can talk and do simple jobs. Every finding below was checked in the sandbox (`sandbox/`) or the physics bench (`sim/`). Numbers are planning estimates until they are measured on real parts.

The updated spreadsheet is `plan/robot_project_plan_v2.xlsx`. Every original row is kept, and new rows are shaded orange.

## What the original plan gets right

- **One module at a time, tested before integration.** This is how working robots get built. v2 keeps the rule and adds one step in front: try it in the twin first.
- **Safety:** wheels raised for first tests, a dead-man timeout, no motors on GPIO pins, trusted Wi-Fi only. These matter more once there are legs and an arm.
- **Motors and drivers.** N20 1:298 motors on TB6612 drivers move the 385 g Hatchling at 0.18 m/s up a 35° ramp in the physics bench. There is plenty of torque.
- **Budget.** The essential parts total (AUD 167–350) matches the sandbox's own parts model (AUD 176–377).

## Adaptations

| # | Change | Why (evidence) |
|---|---|---|
| 1 | Raise ground clearance 5–8 mm, or use bigger wheels | The bench mounts only a 10 mm step on wheels and 15 mm on tracks (44 mm sprockets). The belly catches the edge. The 20 mm kerb goal fails. |
| 2 | Buy N20 motors **with encoders** | Exact distances and turns for the twin, mapping and autonomous jobs. A few dollars more per motor. |
| 3 | Leave a 70 × 35 mm bay and a 5 V 3 A rail for a **Pi Zero 2 W** in the first shell | Video, walking, speech and the hand all need a Linux board. The Pico W stays as the real-time motor, face and safety controller. |
| 4 | Move to a **2S 7.4 V pack with BMS, fuse and switch** before stage 3 | Bus servos need about 7.4 V. 4×AA at 4.8 V is fine for stage 1 only. Charge LiPo under supervision, in a LiPo bag. |
| 5 | **Walking: adopt Open Duck Mini's legs and trained policy** instead of designing new legs | It is open source, proven and runs on a Pi Zero 2 W. Ten STS3215 servos need about a 170 mm body. They will not fit the 120 mm shell. OreVis becomes the duck's head and body. See `sim/OPEN_DUCK.md`. |
| 6 | **One servo family**: Feetech serial-bus servos for legs, arm and hand | One 3-wire bus and one driver board, and the servos report their angle, which the walking policy needs. Open Duck, LeRobot SO-101 and Pollen's Amazing Hand all use them. |
| 7 | **Hand: start with a 45 g three-finger tendon hand** | Pollen's Amazing Hand is about 400 g. The bench shows the 1.36 kg walker tips 44° holding it out. The light hand holds a 20 g block at 64% of shoulder stall with no tipping. Keep the Amazing Hand for a bench-mounted arm later. |
| 8 | Teach the walker to **squat before reaching** | A 17 cm arm mounted 26 cm up can't reach the floor standing. The sandbox squats about 63° at the knee. The bench shows STS3215 knees peak at 36% of stall doing it. |
| 9 | **Avoid hobby servos for legs** | SG90s in a 120 mm mini-duck hit 100% of stall in a squat, and they can't report their angle. |
| 10 | Micro-servo arm on the Hatchling works, but barely | An MG90S shoulder sits at 93% of stall holding a 20 g block out straight. Use a shorter arm or a stronger shoulder servo. |
| 11 | Write behaviours against one small hardware interface (`hal.py`) | The same pick, place and tidy code then runs in the sandbox, in MuJoCo and on the robot. |
| 12 | P04 (set up the computer) no longer waits for parts | The computer, Thonny and the sandbox can be set up while parts ship. |

## Evolution roadmap

| Stage | Name | Adds | Brain | Gate test before moving on |
|---|---|---|---|---|
| 1 | Hatchling | The original plan | Pico W | Sandbox missions 1–2. Bench: 15° ramp |
| 2 | Explorer | Tracks, encoders, live camera | Pico W + Pi Zero 2 W | Bench: 20 mm step (needs adaptation 1) |
| 3 | Duckling | Open Duck legs, IMU, 2S power | Pi Zero 2 W | Bench: stand and squat. Open Duck walks in MuJoCo |
| 4 | Helper | 4-servo arm + 3-finger hand | Pi Zero 2 W | Sandbox tidy-up mission. Bench: arm out, no tipping |
| 5 | Companion | Pi 5, microphone, speaker | Pi 5 | Talk and tidy missions, then the real floor |

Parts cost by stage (AUD, from the sandbox model): Hatchling 176–377, Explorer 256–524, Duckling 503–875, Helper 621–1,075, Companion 711–1,200.

## Known limits of the twin

- The sandbox's quick calculator says the tracked Explorer climbs 22 mm. The physics bench, which models the track as a raised idler plus road wheels, says 15 mm. Trust the lower number until you test real tracks.
- Neither tool makes a biped walk by itself. That is the Open Duck policy's job.
- Servo torques are datasheet stall values with safety margins. Measure real servo loads (the STS3215 reports its load) before trusting a design.
