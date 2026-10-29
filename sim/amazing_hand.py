"""Try Pollen Robotics' Amazing Hand in MuJoCo, using Pollen's own model.

Drives the 8 servos (2 per finger) through the named poses from Pollen's
PythonExample/AmazingHand_Demo.py and reports where the fingertips end up and
the gap between the thumb and each finger, so you can see what sizes of object
the hand can wrap around.

  python sim/amazing_hand.py                 # table of poses
  python sim/amazing_hand.py --view close    # watch a pose in the MuJoCo viewer (needs a display)

Pollen's model is kinematic: its finger links have no collision shapes, so it
shows reach and finger motion, not grip force. The model's printed parts weigh
about 105 g; Pollen quotes about 400 g for the complete hand with servos and screws.
"""
import argparse
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "third_party" / "pollen" / "AmazingHand" / "sim" / "{side}" / "mjcf" / "scene.xml"

# Servo angles in degrees (motor1, motor2) per finger: index, middle, ring, thumb.
# Copied from OpenHand(), CloseHand(), SpreadHand(), ClenchHand() and Index_Pointing()
# in Pollen's AmazingHand_Demo.py (right hand values).
POSES = {
    "open":   [(-35, 35), (-35, 35), (-35, 35), (-35, 35)],
    "close":  [(90, -90), (90, -90), (90, -90), (90, -90)],
    "spread": [(4, 90), (-32, 32), (-90, -4), (-90, -4)],
    "clench": [(-60, 0), (-35, 35), (0, 70), (-4, 90)],
    "point":  [(-40, 40), (90, -90), (90, -90), (90, -90)],
}
FINGERS = ["index", "middle", "ring", "thumb"]


def load(side="AH_Right"):
    model = mujoco.MjModel.from_xml_path(str(MODEL).format(side=side))
    return model, mujoco.MjData(model)


def set_pose(model, data, angles):
    for f, (a1, a2) in enumerate(angles, 1):
        data.ctrl[model.actuator(f"finger{f}_motor1").id] = np.radians(a1)
        data.ctrl[model.actuator(f"finger{f}_motor2").id] = np.radians(a2)


def settle(model, data, angles, seconds=3.0):
    mujoco.mj_resetData(model, data)
    set_pose(model, data, angles)
    for _ in range(int(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
    return np.array([data.site(f"tip{i}").xpos.copy() for i in range(1, 5)])


def report(side="AH_Right"):
    model, data = load(side)
    print(f"Pollen Amazing Hand ({side}): {model.nu} servos, model mass {sum(model.body_mass) * 1000:.0f} g "
          f"(printed parts only; about 400 g complete)")
    print(f"{'pose':8} " + " ".join(f"{'thumb-' + f + ' gap':>17}" for f in FINGERS[:3]) + "   index tip height")
    results = {}
    for name, angles in POSES.items():
        tips = settle(model, data, angles)
        gaps = [np.linalg.norm(tips[3] - tips[i]) * 1000 for i in range(3)]
        results[name] = gaps
        print(f"{name:8} " + " ".join(f"{g:14.0f} mm" for g in gaps) + f"   {tips[0][2] * 1000:8.0f} mm")
    widest, tightest = max(results["open"]), min(results["close"])
    print(f"\nOpen, the thumb tip is up to {widest:.0f} mm from the fingertips; fully closed it is still {tightest:.0f} mm away.")
    print(f"So tip-to-tip it cannot pinch anything smaller than about {tightest:.0f} mm (the sandbox blocks are 30 mm).")
    print("Smaller objects have to be wrapped against the palm, which this model cannot test because its fingers have no")
    print("collision shapes. Try that on the real hand, or with bigger (50 mm) blocks.")
    return results


def view(pose, side="AH_Right"):
    import mujoco.viewer
    model, data = load(side)
    set_pose(model, data, POSES[pose])
    mujoco.viewer.launch(model, data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--side", choices=["AH_Right", "AH_Left"], default="AH_Right")
    ap.add_argument("--view", choices=sorted(POSES), help="open the MuJoCo viewer in this pose")
    a = ap.parse_args()
    if a.view:
        view(a.view, a.side)
    else:
        report(a.side)


if __name__ == "__main__":
    main()
