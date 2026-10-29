"""Build a MuJoCo (MJCF) model of a robot design.

Frame: x forward, y left, z up, metres. The body is a rounded-square box with
four wheels, track sides (approximated by three driven wheels per side) or an
Open Duck style biped (hip roll, hip pitch, knee, ankle pitch per leg). An
optional arm with yaw, shoulder, elbow and wrist servos carries a hand and a
test block.
"""
import math

from design import geometry, masses

MM = 0.001


def _servo_actuator(name, joint, torque, kp_per_nm=40.0):
    # Hobby and bus servos are stiff position controllers that saturate at their stall torque.
    kp = torque * kp_per_nm
    return (f'<position name="{name}" joint="{joint}" kp="{kp:.4f}" kv="{kp * 0.03:.5f}" '
            f'forcelimited="true" forcerange="{-torque:.4f} {torque:.4f}"/>')


def build(d, parts, scenario):
    """scenario: dict with keys such as step_h (m), gravity_slope_deg, arm_pose ('tucked'|'out'), payload (bool)."""
    g = geometry(d)
    m = masses(d, parts)
    w, h = d["body_mm"] * MM, d["height_mm"] * MM
    loco = d["locomotion"]
    acts, worldbody_extra = [], []
    slope = math.radians(scenario.get("gravity_slope_deg", 0))
    gravity = f"{-9.81 * math.sin(slope):.5f} 0 {-9.81 * math.cos(slope):.5f}"

    if scenario.get("step_h"):
        sh = scenario["step_h"]
        sx = w / 2 + 0.04 + 1.0
        worldbody_extra.append(f'<geom name="step" contype="1" conaffinity="2" type="box" pos="{sx:.4f} 0 {sh / 2:.4f}" size="1.0 0.5 {sh / 2:.4f}" rgba=".6 .65 .7 1"/>')

    # ---- locomotion ----
    loco_xml = []
    if loco in ("wheels", "tracks"):
        motor = parts["drive_motors"][d["drive_motor"]]
        wr = d["wheel_mm"] / 2 * MM
        omega0 = motor["rpm"] * 2 * math.pi / 60
        stall = motor["stall_nm"]
        body_z = g["body_bottom"] * MM
        if loco == "wheels":
            xs = [w / 2 - wr * 0.45, -(w / 2 - wr * 0.45)]
            ys = [w * 0.34]
            mu = "0.9 0.005 0.0001"
        else:
            xs = [w * 0.34 + wr * 0.4, w * 0.17, 0.0, -w * 0.17, -w * 0.34]  # idler + road wheels under the belt
            ys = [w / 2 + wr * 0.35]
            mu = "1.2 0.005 0.0001"
        n_wheels = len(xs) * 2
        wheel_mass = (4 * (m["motor"] + m["wheel"])) / n_wheels / 1000
        for i, x in enumerate(xs):
            for side, sgn in (("l", 1), ("r", -1)):
                name = f"w{i}{side}"
                y = sgn * (ys[0] if loco == "tracks" else w * 0.34)
                # A track belt rises over a raised front idler, which meets kerbs and steps first.
                r_i, z_i = (wr * 1.25, wr * 1.6) if (loco == "tracks" and i == 0) else (wr, wr)
                loco_xml.append(
                    f'<body name="{name}" pos="{x:.4f} {y:.4f} {z_i - body_z:.4f}">'
                    f'<joint name="{name}_j" type="hinge" axis="0 1 0" damping="0.0002"/>'
                    f'<geom type="cylinder" size="{r_i:.4f} {wr * 0.45:.4f}" euler="1.5708 0 0" mass="{wheel_mass:.4f}" '
                    f'friction="{mu}" rgba=".08 .09 .1 1" condim="4"/></body>')
                # The four motors share the load when tracks add a middle wheel.
                share = 4 / n_wheels
                acts.append(f'<general name="{name}_m" joint="{name}_j" ctrlrange="-1 1" ctrllimited="true" '
                            f'gainprm="{stall * share:.5f}" biastype="affine" biasprm="0 0 {-stall * share / omega0:.6f}"/>')
        start_z = body_z + 0.002
        legs_info = None
    else:
        servo = parts["servos"][d["leg_servo"]]
        T = servo["stall_nm"]
        sm = servo["mass"] / 1000
        thigh, shin = g["thigh"] * MM, g["shin"] * MM
        fl = g["foot_len"] * MM
        bend = math.radians(g["crouch_deg"])
        printed = m["leg_printed"] / 1000
        hip_drop = 0.012
        for side, sgn in (("l", 1), ("r", -1)):
            y = sgn * g["hip_spread"] * MM
            loco_xml.append(f'''
<body name="hip_{side}" pos="0 {y:.4f} {-hip_drop:.4f}">
  <joint name="hip_roll_{side}" type="hinge" axis="1 0 0" range="-0.5 0.5" damping="0.02" armature="0.002"/>
  <geom type="box" size="{w * 0.08:.4f} {w * 0.06:.4f} {w * 0.05:.4f}" mass="{3 * sm:.4f}" rgba=".14 .16 .18 1"/>
  <body name="thigh_{side}" pos="0 0 0">
    <joint name="hip_pitch_{side}" type="hinge" axis="0 1 0" range="-1.6 1.0" damping="0.02" armature="0.002"/>
    <geom type="capsule" fromto="0 0 0 0 0 {-thigh:.4f}" size="{w * 0.045:.4f}" mass="{printed * 0.5:.4f}" rgba=".95 .42 .11 1"/>
    <body name="shin_{side}" pos="0 0 {-thigh:.4f}">
      <joint name="knee_{side}" type="hinge" axis="0 1 0" range="0 2.4" damping="0.02" armature="0.002"/>
      <geom type="sphere" size="{w * 0.05:.4f}" mass="{sm:.4f}" rgba=".14 .16 .18 1"/>
      <geom type="capsule" fromto="0 0 0 0 0 {-shin:.4f}" size="{w * 0.04:.4f}" mass="{printed * 0.3:.4f}" rgba=".14 .16 .18 1"/>
      <body name="foot_{side}" pos="0 0 {-shin:.4f}">
        <joint name="ankle_{side}" type="hinge" axis="0 1 0" range="-1.4 1.0" damping="0.02" armature="0.002"/>
        <geom type="sphere" size="{w * 0.04:.4f}" mass="{sm:.4f}" rgba=".14 .16 .18 1"/>
        <geom name="sole_{side}" type="box" pos="{fl * 0.18:.4f} 0 -0.004" size="{fl / 2:.4f} {w * 0.1:.4f} 0.004" mass="{printed * 0.2:.4f}" friction="1.0 0.005 0.0001" condim="4" rgba=".95 .42 .11 1"/>
      </body>
    </body>
  </body>
</body>''')
            for j in ("hip_roll", "hip_pitch", "knee", "ankle"):
                acts.append(_servo_actuator(f"{j}_{side}_a", f"{j}_{side}", T))
        stand_h = (thigh + shin) * math.cos(bend) + hip_drop + 0.008
        start_z = stand_h + 0.003
        legs_info = {"bend": bend, "torque": T}

    # ---- arm ----
    arm_xml, arm_info = "", None
    if d.get("arm"):
        aserv = parts["servos"][d["arm_servo"]]
        T = aserv["stall_nm"]
        sm = aserv["mass"] / 1000
        L1, L2 = d["arm_mm"][0] * MM, d["arm_mm"][1] * MM
        hl = g["hand_len"] * MM
        link = m["arm_links"] / 1000
        hand_m = m["hand"] / 1000
        payload = d["payload_g"] / 1000 if scenario.get("payload", True) else 0.0
        bx, by, bz = g["arm_mount_x"] * MM, -w * 0.32, h * 0.82
        aw = max(0.008, w * 0.045)
        arm_xml = f'''
<body name="arm_base" pos="{bx:.4f} {by:.4f} {bz:.4f}">
  <joint name="arm_yaw" type="hinge" axis="0 0 1" range="-2.5 2.5" damping="0.01" armature="0.001"/>
  <geom type="cylinder" size="{aw * 1.4:.4f} {aw * 0.6:.4f}" mass="{2 * sm:.4f}" rgba=".14 .16 .18 1"/>
  <body name="upper" pos="0 0 {aw:.4f}">
    <joint name="shoulder" type="hinge" axis="0 1 0" range="-2.0 2.4" damping="0.01" armature="0.001"/>
    <geom type="box" pos="0 0 {L1 / 2:.4f}" size="{aw:.4f} {aw:.4f} {L1 / 2:.4f}" mass="{link * L1 / (L1 + L2):.4f}" rgba=".95 .42 .11 1"/>
    <body name="fore" pos="0 0 {L1:.4f}">
      <joint name="elbow" type="hinge" axis="0 1 0" range="-0.2 2.8" damping="0.01" armature="0.001"/>
      <geom type="sphere" size="{aw * 1.1:.4f}" mass="{sm:.4f}" rgba=".14 .16 .18 1"/>
      <geom type="box" pos="0 0 {L2 / 2:.4f}" size="{aw * 0.85:.4f} {aw * 0.85:.4f} {L2 / 2:.4f}" mass="{link * L2 / (L1 + L2):.4f}" rgba=".14 .16 .18 1"/>
      <body name="hand" pos="0 0 {L2:.4f}">
        <joint name="wrist" type="hinge" axis="0 1 0" range="-2.0 2.0" damping="0.01" armature="0.001"/>
        <geom type="sphere" size="{aw:.4f}" mass="{sm:.4f}" rgba=".14 .16 .18 1"/>
        <geom name="palm" type="box" pos="0 0 {hl / 2:.4f}" size="{aw * 1.3:.4f} {aw * 0.6:.4f} {hl / 2:.4f}" mass="{hand_m:.4f}" rgba=".95 .42 .11 1"/>
        {"" if payload <= 0 else f'<geom name="payload" type="box" pos="0 0 {hl * 0.8:.4f}" size="0.015 0.015 0.015" mass="{payload:.4f}" rgba=".85 .27 .21 1" contype="0" conaffinity="0"/>'}
      </body>
    </body>
  </body>
</body>'''
        for j in ("arm_yaw", "shoulder", "elbow", "wrist"):
            acts.append(_servo_actuator(f"{j}_a", j, T))
        arm_info = {"torque": T, "L1": L1, "L2": L2, "hl": hl}

    # ---- body ----
    core = m["core"] / 1000
    body_xml = f'''
<body name="chassis" pos="0 0 {start_z:.4f}">
  <freejoint name="root"/>
  <geom name="shell" type="box" pos="0 0 {h / 2:.4f}" size="{w / 2:.4f} {w / 2:.4f} {h / 2:.4f}" mass="{core:.4f}" rgba=".95 .42 .11 1"/>
  <geom type="cylinder" pos="0 0 {h + 0.01:.4f}" size="{w * 0.25:.4f} 0.01" mass="0.001" rgba=".14 .16 .18 1"/>
  <site name="imu" pos="0 0 {h / 2:.4f}"/>
  {"".join(loco_xml)}
  {arm_xml}
</body>'''

    xml = f'''<mujoco model="robot_{d.get('name', 'design').replace(' ', '_')}">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.001" gravity="{gravity}" integrator="implicitfast" cone="elliptic"/>
  <!-- Robot parts (contype 2) touch the world (contype 1) but not each other. -->
  <default><geom contype="2" conaffinity="1" solref="0.004 1" solimp="0.95 0.99 0.001"/></default>
  <visual><global offwidth="960" offheight="640"/></visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1=".82 .84 .86" rgb2=".74 .77 .8" width="300" height="300"/>
    <material name="grid" texture="grid" texrepeat="20 20"/>
  </asset>
  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" diffuse=".8 .8 .8"/>
    <geom name="floor" contype="1" conaffinity="2" type="plane" size="4 4 0.1" material="grid" friction="1.0 0.005 0.0001" condim="4"/>
    {"".join(worldbody_extra)}
    {body_xml}
  </worldbody>
  <actuator>
    {"".join(acts)}
  </actuator>
  <sensor><framequat name="orient" objtype="site" objname="imu"/></sensor>
</mujoco>'''
    return xml, {"legs": legs_info, "arm": arm_info, "start_z": start_z}
