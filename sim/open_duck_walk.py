"""Make the Open Duck Mini walk in MuJoCo with its own trained walking policy.

Follows Open_Duck_Playground's playground/open_duck_mini_v2/mujoco_infer.py:
same model, same 46-number observation (gyro, accelerometer, command, joint
angles and speeds, the last three actions, motor targets, foot contacts, gait
phase), same 50 Hz control, action scale and motor speed limit. It runs
without a window and reports how far and how steadily the duck walks.

  third_party/fetch_open_duck.sh          # once: downloads the model
  python sim/open_duck_walk.py            # walk forward, turn, walk, stop
  python sim/open_duck_walk.py --view     # watch it (needs a display)

The policy (third_party/open_duck/BEST_WALK_ONNX_2.onnx) is from Open_Duck_Mini, Apache 2.0.
"""
import argparse
import math
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime

ROOT = Path(__file__).resolve().parent.parent
DUCK = ROOT / "third_party" / "open_duck"
SCENE = DUCK / "src" / "Open_Duck_Playground" / "playground" / "open_duck_mini_v2" / "xmls" / "scene_flat_terrain.xml"
POLICY = DUCK / "BEST_WALK_ONNX_2.onnx"

SIM_DT, DECIMATION = 0.002, 10          # 500 Hz physics, 50 Hz policy
ACTION_SCALE, DOF_VEL_SCALE = 0.25, 0.05
MAX_MOTOR_VEL = 5.24                    # rad/s
STEPS_IN_PERIOD = 27                    # period 0.54 s x 50 fps, from the reference motion data
CMD_X, CMD_Y, CMD_THETA = 0.15, 0.2, 1.0   # command ranges used in training

# (seconds, [forward m/s, sideways m/s, turn rad/s])
SCRIPT = [(1.0, [0, 0, 0]), (6.0, [0.15, 0, 0]), (3.0, [0, 0, 1.0]), (4.0, [0.15, 0, 0]),
          (3.0, [0, 0, -1.0]), (2.0, [-0.15, 0, 0]), (2.0, [0, 0, 0])]


class Duck:
    def __init__(self):
        if not SCENE.exists():
            raise SystemExit("Open Duck model not found. Run third_party/fetch_open_duck.sh first.")
        m = self.model = mujoco.MjModel.from_xml_path(str(SCENE))
        m.opt.timestep = SIM_DT
        self.data = mujoco.MjData(m)
        self.policy = onnxruntime.InferenceSession(str(POLICY), providers=["CPUExecutionProvider"])
        names = [m.actuator(k).name for k in range(m.nu)]
        self.qpos_addr = np.array([m.jnt_qposadr[m.joint(n).id] for n in names])
        self.qvel_addr = np.array([m.jnt_dofadr[m.joint(n).id] for n in names])
        self.gyro = m.sensor_adr[m.sensor("gyro").id]
        self.acc = m.sensor_adr[m.sensor("accelerometer").id]
        self.floor = m.body("floor").id
        self.feet = [m.body("foot_assembly").id, m.body("foot_assembly_2").id]
        self.default = m.keyframe("home").ctrl.copy()
        self.reset()

    def reset(self):
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[:] = m.keyframe("home").qpos
        d.ctrl[:] = self.default
        mujoco.mj_step(m, d)
        self.last = [np.zeros(m.nu) for _ in range(3)]
        self.motor_targets = self.default.copy()
        self.prev_targets = self.default.copy()
        self.phase_i = 0.0
        self.counter = 0

    def contact(self, foot):
        d, gb = self.data, self.model.geom_bodyid
        for i in range(d.ncon):
            c = d.contact[i]
            if {gb[c.geom1], gb[c.geom2]} == {foot, self.floor}:
                return True
        return False

    def obs(self, command):
        d = self.data
        acc = d.sensordata[self.acc:self.acc + 3].copy()
        acc[0] += 1.3
        phase = self.phase_i / STEPS_IN_PERIOD * 2 * np.pi
        return np.concatenate([
            d.sensordata[self.gyro:self.gyro + 3], acc, command,
            d.qpos[self.qpos_addr] - self.default, d.qvel[self.qvel_addr] * DOF_VEL_SCALE,
            self.last[0], self.last[1], self.last[2], self.motor_targets,
            [float(self.contact(f)) for f in self.feet], [np.cos(phase), np.sin(phase)],
        ]).astype(np.float32)

    def step(self, walk_cmd):
        """One physics step. walk_cmd = [forward, sideways, turn]; the head stays still."""
        mujoco.mj_step(self.model, self.data)
        self.counter += 1
        if self.counter % DECIMATION:
            return
        self.phase_i = (self.phase_i + 1.0) % STEPS_IN_PERIOD
        command = np.array(list(walk_cmd) + [0.0, 0.0, 0.0, 0.0])
        action = self.policy.run(None, {"obs": [self.obs(command)]})[0][0]
        self.last = [action.copy(), self.last[0], self.last[1]]
        targets = self.default + action * ACTION_SCALE
        lim = MAX_MOTOR_VEL * SIM_DT * DECIMATION
        self.motor_targets = np.clip(targets, self.prev_targets - lim, self.prev_targets + lim)
        self.prev_targets = self.motor_targets.copy()
        self.data.ctrl[:] = self.motor_targets

    def base(self):
        d = self.data
        q = d.qpos[3:7]
        yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
        up = 1 - 2 * (q[1] ** 2 + q[2] ** 2)
        return d.qpos[:3].copy(), yaw, math.degrees(math.acos(max(-1, min(1, up))))


def run_script(duck, script=SCRIPT, on_step=None):
    """Drive the duck through (seconds, command) segments. Returns per-segment results."""
    out = []
    for seconds, cmd in script:
        p0, yaw0, _ = duck.base()
        worst_tilt, fell = 0.0, False
        for _ in range(int(seconds / SIM_DT)):
            duck.step(cmd)
            if on_step:
                on_step(cmd)
            p, yaw, tilt = duck.base()
            worst_tilt = max(worst_tilt, tilt)
            fell = fell or p[2] < 0.08 or tilt > 50
        p1, yaw1, _ = duck.base()
        heading = np.array([math.cos(yaw0), math.sin(yaw0)])
        out.append({"cmd": cmd, "seconds": seconds,
                    "forward_m": float(np.dot(p1[:2] - p0[:2], heading)),
                    "turn_deg": math.degrees(math.atan2(math.sin(yaw1 - yaw0), math.cos(yaw1 - yaw0))),
                    "worst_tilt_deg": worst_tilt, "fell": fell})
    return out


def describe(cmd):
    f, s, t = cmd
    if t:
        return f"turn {'left' if t > 0 else 'right'} {abs(t):.1f} rad/s"
    if f:
        return f"walk {'forward' if f > 0 else 'backward'} {abs(f):.2f} m/s"
    return "stand still"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--view", action="store_true", help="watch it in the MuJoCo viewer")
    a = ap.parse_args()
    duck = Duck()
    if a.view:
        import mujoco.viewer
        with mujoco.viewer.launch_passive(duck.model, duck.data) as v:
            run_script(duck, on_step=lambda _c: v.sync())
        return
    print(f"Open Duck Mini, {sum(duck.model.body_mass):.2f} kg, walking with its trained policy")
    results = run_script(duck)
    for r in results:
        print(f"  {describe(r['cmd']):26} {r['seconds']:4.1f} s   moved {r['forward_m'] * 1000:+5.0f} mm   "
              f"turned {r['turn_deg']:+5.0f} deg   max tilt {r['worst_tilt_deg']:4.1f} deg   {'FELL' if r['fell'] else 'upright'}")
    print("Result:", "FELL OVER" if any(r["fell"] for r in results) else "walked the whole script without falling")


if __name__ == "__main__":
    main()
