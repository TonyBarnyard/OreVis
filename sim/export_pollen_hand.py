"""Export Pollen Robotics' Amazing Hand for the browser sandbox.

Runs Pollen's own MuJoCo model of the right hand, moves the 8 servos from the
open pose to each named pose from Pollen's demo code, and records where every
visible part is along the way. The sandbox plays these frames back, so the
hand on screen moves exactly as Pollen's linkages do.

Writes sandbox/pollen_hand.json (layout, colours, poses) and
sandbox/pollen_hand.bin (meshes and frames). Run from the repo root:
  python sim/export_pollen_hand.py
"""
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amazing_hand import POSES, load  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sandbox"
FRAMES = 9          # open -> pose, inclusive
STEP_S = 0.25       # simulated seconds per frame


def main():
    model, data = load("AH_Right")
    geoms = [g for g in range(model.ngeom) if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH]
    mesh_ids = sorted({int(model.geom_dataid[g]) for g in geoms})

    verts, idx, mesh_table = [], [], []
    voff = ioff = 0
    for mid in mesh_ids:
        v0, nv = model.mesh_vertadr[mid], model.mesh_vertnum[mid]
        f0, nf = model.mesh_faceadr[mid], model.mesh_facenum[mid]
        assert nv < 65536
        verts.append(model.mesh_vert[v0:v0 + nv].astype(np.float32))
        idx.append(model.mesh_face[f0:f0 + nf].astype(np.uint16))
        mesh_table.append({"vert_offset": voff, "vert_count": int(nv), "index_offset": ioff, "index_count": int(nf * 3)})
        voff += int(nv)
        ioff += int(nf * 3)

    def colour(g):
        mat = model.geom_matid[g]
        rgba = model.mat_rgba[mat] if mat >= 0 else model.geom_rgba[g]
        return [round(float(c), 3) for c in rgba[:3]]

    geom_table = [{"mesh": mesh_ids.index(int(model.geom_dataid[g])), "rgb": colour(g)} for g in geoms]

    def snapshot():
        out = np.zeros((len(geoms), 7), np.float32)
        q = np.zeros(4)
        for i, g in enumerate(geoms):
            mujoco.mju_mat2Quat(q, data.geom_xmat[g])
            out[i, :3] = data.geom_xpos[g]
            out[i, 3:] = q  # w, x, y, z
        return out

    open_deg = np.array(POSES["open"], float)
    steps = int(STEP_S / model.opt.timestep)
    pose_frames = {}
    for name, target in POSES.items():
        mujoco.mj_resetData(model, data)
        frames = []
        for k in range(FRAMES):
            a = open_deg + (np.array(target, float) - open_deg) * k / (FRAMES - 1)
            for f, (a1, a2) in enumerate(a, 1):
                data.ctrl[model.actuator(f"finger{f}_motor1").id] = np.radians(a1)
                data.ctrl[model.actuator(f"finger{f}_motor2").id] = np.radians(a2)
            for _ in range(steps * (4 if k == 0 else 1)):
                mujoco.mj_step(model, data)
            frames.append(snapshot())
        pose_frames[name] = np.stack(frames)

    frame_blob = np.concatenate([pose_frames[n].ravel() for n in POSES]).astype(np.float32)
    v = np.concatenate(verts).ravel()
    i = np.concatenate(idx).ravel()
    pad = (-i.nbytes) % 4
    blob = v.tobytes() + i.tobytes() + b"\0" * pad + frame_blob.tobytes()
    (OUT / "pollen_hand.bin").write_bytes(blob)
    meta = {
        "source": "Pollen Robotics AmazingHand, Demo/AHSimulation AH_Right (Apache 2.0; meshes CC BY 4.0)",
        "units": "metres; hand frame: fingers along +z, palm faces +x",
        "verts_bytes": int(v.nbytes), "index_bytes": int(i.nbytes), "frames_offset": int(v.nbytes + i.nbytes + pad),
        "meshes": mesh_table, "geoms": geom_table, "frames_per_pose": FRAMES,
        "poses": list(POSES), "servo_degrees": {k: v for k, v in POSES.items()},
    }
    (OUT / "pollen_hand.json").write_text(json.dumps(meta))
    print(f"wrote {len(blob) / 1e6:.2f} MB, {len(geoms)} parts, {len(mesh_ids)} meshes, poses: {', '.join(POSES)}")


if __name__ == "__main__":
    main()
