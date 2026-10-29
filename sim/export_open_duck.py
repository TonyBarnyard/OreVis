"""Export the Open Duck Mini's real walking for the browser sandbox.

Runs the duck with its trained policy (sim/open_duck_walk.py) and records a
looping gait clip for each command: stand, forward, backward, turn left and
turn right. Each frame stores where every visible part is, relative to the
duck's own heading, so the sandbox can play the real gait while moving the
robot around the room itself. The parts are drawn with the full-detail 3D
files from Open_Duck_Mini (Apache 2.0).

Writes sandbox/open_duck.json and sandbox/open_duck.b64.txt. Run from the repo root:
  third_party/fetch_open_duck.sh
  python sim/export_open_duck.py
"""
import base64
import json
import math
import struct
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from open_duck_walk import DECIMATION, DUCK, SIM_DT, STEPS_IN_PERIOD, Duck, describe, run_script  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sandbox"
FULL_PARTS = DUCK / "src" / "Open_Duck_Mini" / "mini_bdx" / "robots" / "open_duck_mini_v2"
SIM_PARTS = DUCK / "src" / "Open_Duck_Playground" / "playground" / "open_duck_mini_v2" / "xmls" / "assets"
CLIPS = {"stand": [0, 0, 0], "forward": [0.15, 0, 0], "backward": [-0.15, 0, 0], "left": [0, 0, 1.0], "right": [0, 0, -1.0]}
FRAMES = 2 * STEPS_IN_PERIOD   # two gait periods at 50 Hz


def read_stl(path):
    b = path.read_bytes()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        v = [list(map(float, l.split()[1:4])) for l in b.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        tri = np.array(v, np.float32)
    else:
        n = struct.unpack("<I", b[80:84])[0]
        a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
        tri = a["v"].reshape(-1, 3).astype(np.float32)
    verts, inverse = np.unique(np.round(tri, 6), axis=0, return_inverse=True)
    return verts.astype(np.float32), inverse.reshape(-1).astype(np.uint32)


def quat_to_mat(q):
    m = np.zeros(9)
    mujoco.mju_quat2Mat(m, q)
    return m.reshape(3, 3)


def main():
    duck = Duck()
    m, d = duck.model, duck.data
    geoms = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_group[g] == 2]
    legs_roots = {m.body("hip_roll_assembly").id, m.body("hip_roll_assembly_2").id}
    head_root = m.body("neck_pitch_assembly").id

    def part_of(body):
        while body > 0:
            if body in legs_roots:
                return "leg"
            if body == head_root:
                return "head"
            body = m.body_parentid[body]
        return "trunk"

    # MuJoCo moves each mesh into its own centred frame; undo that so the original files line up.
    mesh_names = sorted({m.mesh(m.geom_dataid[g]).name for g in geoms})
    mesh_fix = {}
    for name in mesh_names:
        mid = m.mesh(name).id
        mesh_fix[name] = (m.mesh_pos[mid].copy(), quat_to_mat(m.mesh_quat[mid]))
        # check against the simulator's own copy of this part
        sim_v, _ = read_stl(SIM_PARTS / f"{name}.stl")
        p, R = mesh_fix[name]
        moved = (sim_v - p) @ R
        v0, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        mv = m.mesh_vert[v0:v0 + nv]
        err = np.abs(np.r_[moved.min(0) - mv.min(0), moved.max(0) - mv.max(0)]).max()
        assert err < 1e-4, (name, err)

    verts, idx, table = [], [], []
    voff = ioff = 0
    for name in mesh_names:
        v, i = read_stl(FULL_PARTS / f"{name}.stl")
        assert len(v) < 65536, name
        verts.append(v)
        idx.append(i.astype(np.uint16))
        table.append({"name": name, "vert_offset": voff, "vert_count": len(v), "index_offset": ioff, "index_count": len(i)})
        voff += len(v)
        ioff += len(i)

    def colour(g):
        mat = m.geom_matid[g]
        rgba = m.mat_rgba[mat] if mat >= 0 else m.geom_rgba[g]
        return [round(float(c), 3) for c in rgba[:3]]

    geom_table = [{"mesh": mesh_names.index(m.mesh(m.geom_dataid[g]).name), "part": part_of(m.geom_bodyid[g]), "rgb": colour(g)} for g in geoms]

    def snapshot():
        base = d.qpos[:3]
        q = d.qpos[3:7]
        yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
        c, s = math.cos(-yaw), math.sin(-yaw)
        Rh = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        out = np.zeros((len(geoms), 7), np.float32)
        qq = np.zeros(4)
        for k, g in enumerate(geoms):
            p_m, R_m = mesh_fix[m.mesh(m.geom_dataid[g]).name]
            Rg = d.geom_xmat[g].reshape(3, 3)
            R = Rh @ Rg @ R_m.T
            pos = Rh @ (d.geom_xpos[g] - Rg @ R_m.T @ p_m - np.array([base[0], base[1], 0]))
            mujoco.mju_mat2Quat(qq, R.ravel())
            out[k, :3], out[k, 3:] = pos, qq
        return out

    clips, motion = [], {}
    for name, cmd in CLIPS.items():
        duck.reset()
        run_script(duck, [(1.0, [0, 0, 0]), (3.0, cmd)])
        p0, yaw0, _ = duck.base()
        frames = []
        steps = 0
        while len(frames) < FRAMES:
            duck.step(cmd)
            steps += 1
            if steps % DECIMATION == 0:
                frames.append(snapshot())
        p1, yaw1, _ = duck.base()
        t = steps * SIM_DT
        h = np.array([math.cos(yaw0), math.sin(yaw0)])
        motion[name] = {"forward_mps": round(float(np.dot(p1[:2] - p0[:2], h)) / t, 4),
                        "turn_radps": round(math.atan2(math.sin(yaw1 - yaw0), math.cos(yaw1 - yaw0)) / t, 4)}
        clips.append(np.stack(frames))

    duck.reset()
    script = run_script(duck)
    v = np.concatenate(verts).ravel()
    i = np.concatenate(idx).ravel()
    pad = (-i.nbytes) % 4
    frames_blob = np.concatenate([c.ravel() for c in clips]).astype(np.float32)
    blob = v.tobytes() + i.tobytes() + b"\0" * pad + frames_blob.tobytes()
    (OUT / "open_duck.b64.txt").write_text(base64.b64encode(blob).decode("ascii"))
    meta = {
        "source": "Open Duck Mini v2 by Antoine Pirrone and contributors: parts from Open_Duck_Mini (Apache 2.0), "
                  "gait from its BEST_WALK_ONNX_2 policy run in MuJoCo",
        "units": "metres; z up, x forward; poses relative to the duck's heading",
        "verts_bytes": int(v.nbytes), "index_bytes": int(i.nbytes), "frames_offset": int(v.nbytes + i.nbytes + pad),
        "meshes": table, "geoms": geom_table, "clips": list(CLIPS), "frames_per_clip": FRAMES, "fps": 50,
        "motion": motion,
        "mass_kg": round(float(sum(m.body_mass)), 2),
        "test_walk": [{"what": describe(r["cmd"]), "seconds": r["seconds"], "moved_mm": round(r["forward_m"] * 1000),
                       "turned_deg": round(r["turn_deg"]), "fell": r["fell"]} for r in script],
    }
    (OUT / "open_duck.json").write_text(json.dumps(meta))
    print(f"wrote {len(blob) / 1e6:.2f} MB ({len(geoms)} parts, {len(mesh_names)} meshes, {sum(t['index_count'] for t in table) // 3} triangles)")
    for k, mo in motion.items():
        print(f"  {k:9} {mo['forward_mps']:+.3f} m/s  {math.degrees(mo['turn_radps']):+6.1f} deg/s")


if __name__ == "__main__":
    main()
