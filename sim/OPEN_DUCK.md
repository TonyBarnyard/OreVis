# Walking: using the Open Duck Mini

The sandbox and `bench.py` can tell you if a pair of legs is strong enough to stand and squat. They cannot make a biped walk. Walking needs a learned policy: a small neural network that reads the IMU and joint angles 50 times a second and decides where every servo goes next. The Open Duck Mini project has already done this work, and it is open source (Apache-2.0), so the plan is to reuse it rather than start from scratch.

| Repo | What it is |
|---|---|
| [Open_Duck_Mini](https://github.com/apirrone/Open_Duck_Mini) | CAD, bill of materials, assembly. About 42 cm tall, BOM target under US$400, Raspberry Pi Zero 2 W brain. |
| [Open_Duck_Playground](https://github.com/apirrone/Open_Duck_Playground) | Trains walking policies in MuJoCo Playground. |
| [Open_Duck_reference_motion_generator](https://github.com/apirrone/Open_Duck_reference_motion_generator) | Makes the reference gait the policy learns to imitate. |
| [Open_Duck_Mini_Runtime](https://github.com/apirrone/Open_Duck_Mini_Runtime) | Runs the trained policy on the robot. |

## Recommended route

1. **Build the duck's legs as designed.** Don't redesign the legs. The published policy was trained for that exact mass, leg geometry and servo behaviour, so a stock duck walks on day one. OreVis becomes the "head and body": the orange shell, the face screen and the spiral camera mount sit on top. Keep the extra mass under about 150 g and keep it centred, or the policy will need retraining.
2. **Run the stock policy in simulation first.** Install `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`), clone Open_Duck_Playground, then run its MuJoCo inference script with a trained ONNX policy:
   ```
   uv run playground/open_duck_mini_v2/mujoco_infer.py -o <path_to_.onnx>
   ```
3. **Then on the real robot**, follow the Open_Duck_Mini_Runtime README: Raspberry Pi OS Lite 64-bit on the Pi Zero 2 W, I2C on, IMU test, `scripts/check_motors.py`, joint offsets, then
   ```
   cd scripts/
   python v2_rl_walk_mujoco.py --onnx_model_path <path_to>/BEST_WALK_ONNX_2.onnx
   ```
4. **Retrain only when the body changes a lot.** For example, when you add the arm and hand at stage 4. Copy `playground/open_duck_mini_v2` to `playground/orevis`, swap in your own MJCF (start from `python sim/bench.py sim/designs/4_helper.json --xml`, which writes `sim/out/helper.xml`, or better, edit the duck's own model), then:
   ```
   uv run playground/orevis/runner.py --task flat_terrain_backlash --num_timesteps 300000000
   uv run tensorboard --logdir=<yourlogdir>
   ```
   Training runs that long need a computer with a decent NVIDIA GPU, or a rented cloud GPU for a few hours. Don't try it on the Pi.

## What the OreVis bench already tells you before you train

- STS3215 knees hold the 1.36 kg Helper in a crouch at about 7% of stall, and peak at about 36% during a full squat. There is room left for walking.
- SG90 hobby servos reach 100% of stall in the same squat on a 120 mm mini duck. They also can't report their angle, which the policy needs. Use bus servos.
- A walking robot with a 17 cm arm mounted 26 cm up can't reach the floor standing up. It has to squat, so the policy for stage 4 needs a "squat and reach" behaviour as well as walking.

These numbers come from the model and simulation, not from real servos. Check them on the bench with the real parts (`Wiring & Test Log` sheet).
