"""Load robot designs and the shared parts library.

The parts library lives in sandbox/parts.js so the browser sandbox and this
physics bench always use the same numbers. Designs are the JSON the sandbox
exports ("Design file for the physics tests").
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS_JS = ROOT / "sandbox" / "parts.js"

DEFAULT_DESIGN = {
    "name": "Hatchling", "body_mm": 120, "height_mm": 80, "locomotion": "wheels",
    "drive_motor": "n20_100rpm", "wheel_mm": 34, "leg_servo": "sts3215", "leg_mm": 160,
    "arm": False, "arm_servo": "mg90s", "arm_mm": [60, 55], "hand": "gripper2",
    "brain": "pico_w", "battery": "aa4_nimh", "voice": False, "mast_mm": 20, "payload_g": 20,
}


def load_parts():
    text = PARTS_JS.read_text()
    start = text.index("window.ROBOT_PARTS =") + len("window.ROBOT_PARTS =")
    return json.loads(text[start:].strip().rstrip(";"))


def load_design(path=None):
    design = dict(DEFAULT_DESIGN)
    if path:
        design.update(json.loads(Path(path).read_text()))
    return design


def hand_length_mm(hand):
    return {"amazing_hand": 110, "micro_hand": 50}.get(hand, 35)


def geometry(d):
    """Mirror of geometry() in sandbox/model.js, in millimetres."""
    w, h, wr = d["body_mm"], d["height_mm"], d["wheel_mm"] / 2
    g = {"body_w": w, "body_h": h, "wheel_r": wr}
    if d["locomotion"] == "legs":
        g["crouch_deg"] = 22
        g["thigh"] = g["shin"] = d["leg_mm"] / 2
        g["foot_len"] = max(40, d["leg_mm"] * 0.45)
        g["hip_spread"] = w * 0.26
        g["body_bottom"] = d["leg_mm"] * math.cos(math.radians(22)) + 8
        g["support_half"] = g["foot_len"] / 2
    elif d["locomotion"] == "tracks":
        g["body_bottom"] = wr * 0.7
        g["support_half"] = w * 0.45
    else:
        g["body_bottom"] = wr * 0.6
        g["support_half"] = w * 0.38
    g["arm_mount_x"] = w * 0.25
    g["hand_len"] = hand_length_mm(d["hand"])
    return g


def masses(d, parts):
    """Mass budget in grams, split into the parts the physics model needs."""
    C, F = parts["constants"], parts["fixed"]
    w, h = d["body_mm"], d["height_mm"]
    brain = parts["brains"][d["brain"]]
    shell = (2 * w * w + 4 * w * h) * C["shell_wall_mm"] * C["pla_density_g_cm3"] / 1000 * C["shell_fill_factor"]
    core = shell + brain["mass"] + parts["batteries"][d["battery"]]["mass"]
    core += sum(F[k]["mass"] for k in ("display", "tof_sensor", "cam_servo", "wiring"))
    if brain["video"]:
        core += F["camera"]["mass"]
    if d.get("voice"):
        core += F["voice_kit"]["mass"]
    m = {"core": core}
    if d["locomotion"] == "legs":
        servo = parts["servos"][d["leg_servo"]]
        m["leg_servo"] = servo["mass"]
        m["leg_printed"] = d["leg_mm"] * 0.18          # per leg
        core += F["imu"]["mass"] + (F["bus_board"]["mass"] if servo["feedback"] else 0)
        m["core"] = core
    else:
        m["motor"] = parts["drive_motors"][d["drive_motor"]]["mass"]
        m["wheel"] = F["wheel"]["mass"]
        if d["locomotion"] == "tracks":
            m["core"] += F["track_set"]["mass"]
    if d.get("arm"):
        m["arm_servo"] = parts["servos"][d["arm_servo"]]["mass"]
        m["arm_links"] = (d["arm_mm"][0] + d["arm_mm"][1]) * 0.12
        m["hand"] = parts["hands"][d["hand"]]["mass"]
        leg_bus = d["locomotion"] == "legs" and parts["servos"][d["leg_servo"]]["feedback"]
        if parts["servos"][d["arm_servo"]]["feedback"] and not leg_bus:
            m["core"] += F["bus_board"]["mass"]
    return m


def total_mass_g(d, parts):
    m = masses(d, parts)
    total = m["core"]
    if d["locomotion"] == "legs":
        total += 10 * m["leg_servo"] + 2 * m["leg_printed"]
    else:
        total += 4 * (m["motor"] + m["wheel"])
    if d.get("arm"):
        total += 4 * m["arm_servo"] + m["arm_links"] + m["hand"]
    return total
