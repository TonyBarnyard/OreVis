"""OreVis physics test bench (MuJoCo).

Runs the same design the browser sandbox exports through rigid-body physics:

  wheels / tracks : top speed, steepest ramp it can climb, tallest step it can mount
  legs            : stand in a crouch, squat to floor-reach depth and stand back up
  arm             : hold the arm straight out with the test block (shoulder sag, tipping)

Usage:
  python sim/bench.py                         # stage 1 Hatchling defaults
  python sim/bench.py sim/designs/helper.json
  python sim/bench.py sim/designs/*.json --json results.json
  python sim/bench.py sim/designs/helper.json --view squat   # open the MuJoCo viewer (needs a display)

Walking itself is not scripted here: a walking gait for a biped needs a learned
policy. See sim/OPEN_DUCK.md for training one with the Open Duck Playground.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from design import load_design, load_parts, total_mass_g  # noqa: E402
from robot_xml import build  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def make(d, parts, **scenario):
    xml, info = build(d, parts, scenario)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    return model, data, info, xml


def pitch_deg(data):
    q = data.sensor("orient").data  # w, x, y, z
    w, x, y, z = q
    # tilt of the body's up axis from vertical
    up_z = 1 - 2 * (x * x + y * y)
    return math.degrees(math.acos(max(-1.0, min(1.0, up_z))))


def set_ctrl(model, data, name, value):
    data.ctrl[model.actuator(name).id] = value


def legs_pose(model, data, bend, roll=0.0):
    for s in ("l", "r"):
        set_ctrl(model, data, f"hip_roll_{s}_a", 0.0)
        set_ctrl(model, data, f"hip_pitch_{s}_a", -bend)
        set_ctrl(model, data, f"knee_{s}_a", 2 * bend)
        set_ctrl(model, data, f"ankle_{s}_a", -bend)


def init_legs(model, data, bend):
    for s in ("l", "r"):
        data.joint(f"hip_pitch_{s}").qpos = -bend
        data.joint(f"knee_{s}").qpos = 2 * bend
        data.joint(f"ankle_{s}").qpos = -bend
    legs_pose(model, data, bend)


def arm_pose(model, data, pose):
    # tucked: folded over the body; out: straight out in front, horizontal (worst case for the shoulder)
    targets = {"tucked": (0, -0.4, 2.4, 1.2), "out": (0, math.pi / 2, 0, 0)}[pose]
    for j, v in zip(("arm_yaw", "shoulder", "elbow", "wrist"), targets):
        set_ctrl(model, data, f"{j}_a", v)
    return targets


def init_arm(model, data, pose="tucked"):
    t = arm_pose(model, data, pose)
    for j, v in zip(("arm_yaw", "shoulder", "elbow", "wrist"), t):
        data.joint(j).qpos = v


def prepare(model, data, d, info, arm="tucked"):
    mujoco.mj_resetData(model, data)
    if d["locomotion"] == "legs":
        init_legs(model, data, info["legs"]["bend"])
    if d.get("arm"):
        init_arm(model, data, arm)
    mujoco.mj_forward(model, data)


def run(model, data, seconds, each=None):
    steps = int(seconds / model.opt.timestep)
    for i in range(steps):
        if each:
            each(i * model.opt.timestep)
        mujoco.mj_step(model, data)


def chassis_pos(data):
    return data.body("chassis").xpos.copy()


def drive(model, data, u):
    for a in range(model.nu):
        if model.actuator(a).name.endswith("_m"):
            data.ctrl[a] = u


# ---------------- tests ----------------

def test_speed(d, parts):
    model, data, info, _ = make(d, parts)
    prepare(model, data, d, info)
    run(model, data, 0.5)
    drive(model, data, 1.0)
    run(model, data, 1.5)
    x0 = chassis_pos(data)[0]
    run(model, data, 2.0)
    return (chassis_pos(data)[0] - x0) / 2.0


def climbs_slope(d, parts, deg):
    model, data, info, _ = make(d, parts, gravity_slope_deg=deg)
    prepare(model, data, d, info)
    drive(model, data, 1.0)
    run(model, data, 3.0)
    p = chassis_pos(data)
    return p[0] > 0.15 and pitch_deg(data) < 60


def max_slope(d, parts):
    best = 0
    for deg in range(5, 50, 5):
        if climbs_slope(d, parts, deg):
            best = deg
        else:
            break
    return best


def mounts_step(d, parts, h):
    model, data, info, _ = make(d, parts, step_h=h)
    prepare(model, data, d, info)
    run(model, data, 0.3)  # settle onto the wheels first
    z0 = chassis_pos(data)[2]
    drive(model, data, 1.0)
    run(model, data, 4.0)
    p = chassis_pos(data)
    step_x = d["body_mm"] / 2000 + 0.04
    return p[0] > step_x + 0.02 and p[2] > z0 + 0.6 * h and pitch_deg(data) < 60


def max_step(d, parts):
    """Tallest step mounted, and any lower heights that failed (a sign the result is borderline)."""
    ok = [mm for mm in range(5, 45, 5) if mounts_step(d, parts, mm / 1000)]
    best = max(ok) if ok else 0
    return best, [mm for mm in range(5, best, 5) if mm not in ok]


def test_stand_and_squat(d, parts):
    model, data, info, _ = make(d, parts)
    prepare(model, data, d, info)
    bend0 = info["legs"]["bend"]
    T = info["legs"]["torque"]
    knee_ids = [model.actuator(f"knee_{s}_a").id for s in ("l", "r")]
    z_target = chassis_pos(data)[2]
    peak = {"v": 0.0}

    def track(_t):
        peak["v"] = max(peak["v"], max(abs(data.actuator_force[k]) for k in knee_ids))

    # settle, then average the knee load once the landing bounce is over
    run(model, data, 1.0)
    loads = []
    run(model, data, 1.0, lambda _t: loads.append(max(abs(data.actuator_force[k]) for k in knee_ids)))
    stand_z = chassis_pos(data)[2]
    stand_ok = pitch_deg(data) < 20 and stand_z > 0.8 * z_target
    stand_peak = float(np.mean(loads))

    # squat to the depth the sandbox uses for floor pickups, hold, then stand up
    deep = 1.1
    def squat(t):
        if t < 0.3:
            return
        t -= 0.3
        frac = min(1.0, t / 1.0) if t < 2.0 else max(0.0, 1 - (t - 2.0) / 1.0)
        legs_pose(model, data, bend0 + frac * (deep - bend0))
        track(t)
    peak["v"] = 0.0
    run(model, data, 3.5, squat)
    end_z = chassis_pos(data)[2]
    squat_ok = pitch_deg(data) < 20 and end_z > 0.9 * stand_z
    return {
        "stand_ok": bool(stand_ok), "stand_height_mm": round(stand_z * 1000),
        "stand_knee_load": round(stand_peak / T, 2),
        "squat_ok": bool(squat_ok), "squat_knee_load": round(peak["v"] / T, 2),
    }


def test_arm_hold(d, parts):
    model, data, info, _ = make(d, parts, payload=True)
    prepare(model, data, d, info, arm="out")
    if d["locomotion"] in ("wheels", "tracks"):
        drive(model, data, 0.0)
    if d["locomotion"] == "legs":
        legs_pose(model, data, info["legs"]["bend"])
    T = info["arm"]["torque"]
    sh = model.actuator("shoulder_a").id
    worst_tilt, peak = 0.0, 0.0

    def watch(_t):
        nonlocal worst_tilt, peak
        worst_tilt = max(worst_tilt, pitch_deg(data))
        peak = max(peak, abs(data.actuator_force[sh]))

    run(model, data, 3.0, watch)
    sag = math.degrees(abs(math.pi / 2 - data.joint("shoulder").qpos[0]))
    return {
        "shoulder_sag_deg": round(sag, 1), "shoulder_load": round(peak / T, 2),
        "body_tilt_deg": round(worst_tilt, 1),
        "holds": bool(sag < 8 and worst_tilt < 20), "tips": bool(worst_tilt >= 20),
    }


def model_prediction(d):
    """The sandbox's hand calculation (sandbox/model.js), if node is available."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        return None
    root = Path(__file__).resolve().parent.parent / "sandbox"
    js = ("global.window=global;require(process.argv[1]+'/parts.js');const M=require(process.argv[1]+'/model.js');"
          "const r=M.evaluate(JSON.parse(process.argv[2]),window.OREVIS_PARTS);"
          "console.log(JSON.stringify({speed:r.speed_mps,step:r.step_mm,checks:r.checks.map(c=>[c.id,c.status])}))")
    try:
        out = subprocess.run([node, "-e", js, str(root), json.dumps(d)], capture_output=True, text=True, timeout=20)
        return json.loads(out.stdout)
    except Exception:  # the comparison is optional
        return None


def bench(d, parts):
    res = {"name": d.get("name", "design"), "locomotion": d["locomotion"], "mass_g": round(total_mass_g(d, parts))}
    if d["locomotion"] in ("wheels", "tracks"):
        res["top_speed_mps"] = round(test_speed(d, parts), 3)
        res["max_ramp_deg"] = max_slope(d, parts)
        res["max_step_mm"], res["step_misses_mm"] = max_step(d, parts)
    else:
        res.update(test_stand_and_squat(d, parts))
    if d.get("arm"):
        res["arm"] = test_arm_hold(d, parts)
    res["sandbox_prediction"] = model_prediction(d)
    return res


def verdict(ok):
    return "PASS" if ok else "FAIL"


def report(r):
    lines = [f"\n== {r['name']} ({r['locomotion']}, {r['mass_g']} g) =="]
    if "top_speed_mps" in r:
        lines.append(f"  top speed on the flat     {r['top_speed_mps']:.2f} m/s")
        lines.append(f"  steepest ramp climbed     {r['max_ramp_deg']} deg   {verdict(r['max_ramp_deg'] >= 15)} (goal 15 deg)")
        miss = f"  (but stuck at {', '.join(map(str, r['step_misses_mm']))} mm: borderline)" if r["step_misses_mm"] else ""
        lines.append(f"  tallest step mounted      {r['max_step_mm']} mm    {verdict(r['max_step_mm'] >= 20)} (goal 20 mm){miss}")
    if "stand_ok" in r:
        lines.append(f"  stands in a crouch        {verdict(r['stand_ok'])}  height {r['stand_height_mm']} mm, knee at {r['stand_knee_load']:.0%} of stall")
        lines.append(f"  squat and stand up        {verdict(r['squat_ok'])}  knee peak {r['squat_knee_load']:.0%} of stall during the squat")
    if "arm" in r:
        a = r["arm"]
        lines.append(f"  arm out with block        {verdict(a['holds'])}  shoulder sag {a['shoulder_sag_deg']} deg at {a['shoulder_load']:.0%} of stall, body tilt {a['body_tilt_deg']} deg"
                     + ("  <- TIPS OVER" if a["tips"] else ""))
    p = r.get("sandbox_prediction")
    if p:
        lines.append("  sandbox hand calc says    " + ", ".join(f"{k}:{s}" for k, s in p["checks"]))
    return "\n".join(lines)


def view(d, parts, what):
    import mujoco.viewer
    scen = {"step": {"step_h": 0.02}}.get(what, {})
    model, data, info, _ = make(d, parts, **scen)
    prepare(model, data, d, info, arm="out" if what == "arm" else "tucked")
    with mujoco.viewer.launch_passive(model, data) as v:
        t0 = data.time
        while v.is_running():
            t = data.time - t0
            if d["locomotion"] in ("wheels", "tracks"):
                drive(model, data, 1.0 if what in ("drive", "step") else 0.0)
            elif what == "squat":
                b0 = info["legs"]["bend"]
                legs_pose(model, data, b0 + (1.1 - b0) * 0.5 * (1 - math.cos(t * 1.5)))
            mujoco.mj_step(model, data)
            v.sync()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("designs", nargs="*", help="design JSON files exported from the sandbox")
    ap.add_argument("--json", help="write all results to this JSON file")
    ap.add_argument("--xml", action="store_true", help="also save each MJCF model to sim/out/")
    ap.add_argument("--view", choices=["drive", "step", "stand", "squat", "arm"], help="open the interactive MuJoCo viewer")
    a = ap.parse_args()
    parts = load_parts()
    designs = [load_design(p) for p in a.designs] or [load_design()]
    if a.view:
        view(designs[0], parts, a.view)
        return
    results = []
    for d in designs:
        r = bench(d, parts)
        results.append(r)
        print(report(r), flush=True)
        if a.xml:
            OUT.mkdir(exist_ok=True)
            xml, _ = build(d, parts, {})
            (OUT / f"{d.get('name', 'design').replace(' ', '_').lower()}.xml").write_text(xml)
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
