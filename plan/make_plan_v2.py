"""Make robot_project_plan_v2.xlsx from the original plan.

Keeps every original sheet and row, then adds the review, the evolution
roadmap, later-stage parts and the sandbox/physics results.
Run from the repo root: python plan/make_plan_v2.py
"""
import json
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
SRC = HERE / "robot_project_plan.xlsx"
DST = HERE / "robot_project_plan_v2.xlsx"
RESULTS = HERE.parent / "sim" / "results.json"

NAVY = "0019465A"
BAND = "00F3F7F8"
NEW = "00FFF4E8"   # light orange: rows added in v2
thin = Side(style="thin", color="00C9D3D8")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
HEAD_FONT = Font(bold=True, color="00FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor=NAVY)
WRAP_TOP = Alignment(wrap_text=True, vertical="top")
STATUS = '"Not started,In progress,Blocked,Complete"'


def title(ws, text, sub):
    ws["A1"] = text
    ws["A1"].font = Font(bold=True, size=18, color="00FFFFFF")
    ws["A1"].fill = HEAD_FILL
    ws["A2"] = sub
    ws["A2"].font = Font(size=10, color="00666666")
    ws.merge_cells("A1:F1")
    ws.merge_cells("A2:F2")


def header(ws, row, names):
    for i, n in enumerate(names, 1):
        c = ws.cell(row, i, n)
        c.font, c.fill, c.border = HEAD_FONT, HEAD_FILL, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = 30


def rows(ws, start, data, fill=None):
    for r, vals in enumerate(data, start):
        for c, v in enumerate(vals, 1):
            cell = ws.cell(r, c, v)
            cell.alignment, cell.border = WRAP_TOP, BORDER
            f = fill or (BAND if (r - start) % 2 == 0 else None)
            if f:
                cell.fill = PatternFill("solid", fgColor=f)
    return start + len(data)


def section(ws, row, text, width):
    c = ws.cell(row, 1, text)
    c.font = Font(bold=True, color=NAVY, size=12)
    for i in range(1, width + 1):
        ws.cell(row, i).border = Border(bottom=Side(style="medium", color=NAVY))


def widths(ws, ws_widths):
    for col, w in ws_widths.items():
        ws.column_dimensions[col].width = w


# ---------------------------------------------------------------- content

REVIEW = [
    ("Keep", "Staged, test-each-module-first approach", "This is the right way to build robots. Every later stage in v2 follows the same rule: prove it in the sandbox, then on the bench, then on the floor.", "No change"),
    ("Keep", "Safety rules (wheels raised, dead-man timeout, no motors on GPIO, trusted Wi-Fi only)", "These are correct and they matter more once the robot has legs and an arm. They are copied into every new stage.", "No change"),
    ("Keep", "N20 1:298 motors with TB6612 drivers", "Physics bench: the 385 g Hatchling reaches 0.18 m/s and climbs a 35 degree ramp. Plenty of torque. The TB6612 (1.2 A per channel continuous) suits N20 stall currents.", "No change"),
    ("Adapt", "Ground clearance limits steps to about 10 mm", "Physics bench: wheels mount 10 mm and the tracked version 15 mm (with 44 mm sprockets). Neither manages the 20 mm kerb goal. The belly hits the edge.", "Raise the floor of the shell by 5 to 8 mm, or use bigger wheels. Test again in sim/bench.py."),
    ("Adapt", "Choose N20 motors with hall encoders", "Encoders count wheel turns. The robot can then drive exact distances, which the digital twin and autonomous tasks need. They cost a few dollars more per motor.", "Change E04 to encoder N20s (6 extra Pico pins)"),
    ("Adapt", "Plan the shell around two brains from day one", "Pico W is right for stage 1 (motors, face, sensor). Video, walking, speech and the hand all need a Linux board. A Pi Zero 2 W is 65 x 30 mm.", "Leave a 70 x 35 mm bay and a 5 V 3 A supply rail in the stage 1 shell"),
    ("Adapt", "Power: move to a 2S (7.4 V) pack with a BMS before stage 3", "Bus servos (STS3215) need about 7.4 V. 4x AA NiMH at 4.8 V is fine for stage 1 only. Add a fuse, a switch and a 5 V buck converter for the Pi.", "New part U07 and U08; supervised charging in a LiPo bag"),
    ("Adapt", "Walking: adopt the Open Duck Mini legs and policy, don't design new legs", "Open Duck Mini is open source (Apache-2.0), about 42 cm tall, uses a Pi Zero 2 W and already has a trained walking policy. Ten STS3215 servos will not fit in a 120 mm body: they need about a 170 mm body.", "Stage 3 = build the duck's legs and put the round robot shell, face and camera on top. Keep added mass under about 150 g. See sim/OPEN_DUCK.md"),
    ("Adapt", "Use one servo family for legs, arm and hand", "Feetech serial-bus servos (STS3215, SCS0009) share one 3-wire bus and one driver board, and report their angle. Open Duck, the LeRobot SO-101 arm and Pollen's Amazing Hand all use them.", "Standardise on Feetech bus servos for stages 3 to 5"),
    ("Adapt", "Hand: start with a light 3-finger hand, not the full humanoid hand", "Pollen's Amazing Hand is about 400 g. The physics bench shows the 1.36 kg walker tips 44 degrees holding it out. A 45 g 3-finger tendon hand holds a 20 g block at 64% of shoulder stall with no tipping.", "Stage 4 = 3-finger hand. Try the Amazing Hand later on a bench-mounted arm"),
    ("Adapt", "A walking robot must squat to pick things off the floor", "Sandbox: with a 17 cm arm mounted 26 cm up, the Helper only reaches the floor by squatting about 63 degrees at the knee. The bench shows STS3215 knees peak at 36% of stall in that squat, which is fine.", "Add a squat-and-reach behaviour (sandbox already does it)"),
    ("Adapt", "Use Pollen Robotics' open-source Amazing Hand files", "Pollen publish the hand's print files (CC BY 4.0), servo code and a MuJoCo model (Apache 2.0). A copy is in third_party/pollen; python sim/amazing_hand.py runs their model through their named poses. Closed, the fingertips stop about 46 mm from the thumb, so tip-to-tip it can't pinch the 30 mm test blocks.", "Use their files as-is for the bench-mounted hand; test with 50 mm objects first"),
    ("Adapt", "Stage 5 voice: start from Pollen's Reachy Mini conversation app", "Reachy Mini's SDK and conversation app are open source (Apache 2.0) and already connect a microphone, a speaker and a language model to a small robot.", "third_party/fetch_pollen.sh downloads it; adapt its voice loop for P30-P31"),
    ("Adapt", "Software: write behaviours once, run them in the twin and on the robot", "Give motors, servos and sensors the same small interface in the sandbox, MuJoCo and the robot. Tested behaviour code can then move to hardware unchanged.", "New software row 10: hal.py"),
    ("Fix", "P04 does not need to wait for parts (P03)", "The computer, Thonny and the sandbox can all be set up while parts ship.", "P04 dependency changed to None"),
    ("Fix", "P18 live video now has a home", "Stage 2 adds the Pi Zero 2 W, which streams the camera. The Pico keeps doing motors and the face.", "P18 linked to stage 2 tasks"),
]

ROADMAP = [
    ("1", "Hatchling", "The original plan: rounded-square body, four wheels, Pico W, colour face, VL53L0X, camera tilt servo, phone control.",
     "Pico W", "4x N20 wheels", "Drive, face, stop for obstacles", "Sandbox missions 1-2; bench: 15 degree ramp", "385 g", "$176-377"),
    ("2", "Explorer", "Track panels on 44 mm sprockets, Pi Zero 2 W + camera for live video. Encoders for exact moves.",
     "Pico W + Pi Zero 2 W", "Tracks", "Live video, kerbs, mapping the room", "Bench: step >= 20 mm (needs more clearance)", "432 g", "$256-524"),
    ("3", "Duckling", "Grows legs: Open Duck Mini v2 legs (10x STS3215), BNO055 IMU, 2S battery. The round robot shell becomes the head and body.",
     "Pi Zero 2 W", "Two legs", "Walks with the Open Duck policy", "Bench: stand + squat; Open Duck MuJoCo inference walks", "about 1.1 kg", "$503-875"),
    ("4", "Helper", "Adds a 4-servo STS3215 arm and a 3-finger tendon hand on the right shoulder.",
     "Pi Zero 2 W", "Two legs", "Squat, pick a block, carry it to a bin", "Sandbox: Tidy-up mission; bench: arm hold, no tipping", "about 1.4 kg", "$621-1075"),
    ("5", "Companion", "Pi 5 brain, microphone and speaker. Talks, listens and plans simple jobs.",
     "Pi 5 (4 GB)", "Two legs", "Talk, follow spoken requests, do tasks alone", "Sandbox: talk and tidy missions", "about 1.4 kg", "$711-1200"),
]

TASKS = [
    ("P00", "Try the design in the sandbox", "Open sandbox/index.html. Drive the Hatchling, finish missions 1-2, then try other motors, wheels and batteries. Save the designs you like and compare them.", "None", "1-2 hours"),
    ("P19", "Stage 2: add encoders and a Pi Zero 2 W", "Swap to encoder N20s. Mount the Pi Zero 2 W in the reserved bay. Link it to the Pico over UART (TX/RX/GND). The Pico keeps the motors and the dead-man stop.", "P15", "4-6 hours"),
    ("P20", "Stage 2: live camera", "Fit the Pi camera to the spiral mount. Stream video on the local network only. Check the stream does not slow the Pico's stop command.", "P19", "3-5 hours"),
    ("P21", "Stage 2: tracks", "Fit 44 mm sprockets and track panels (P17). Run sim/bench.py on your measured design first; raise ground clearance until the bench mounts 20 mm.", "P17, P19", "Variable"),
    ("P22", "Stage 3: run Open Duck in simulation", "Install uv and Open_Duck_Playground. Run mujoco_infer.py with a trained policy and watch the duck walk. No hardware needed.", "P00", "2-3 hours"),
    ("P23", "Stage 3: build the duck legs", "Print and assemble the Open Duck Mini v2 legs. Set each STS3215 servo ID and test it alone with the bus board before assembly.", "P22", "15-25 hours"),
    ("P24", "Stage 3: power and IMU", "2S pack with BMS, fuse, switch and 5 V 3 A buck for the Pi. Fit the BNO055 IMU near the centre of the body and test it.", "P23", "3-5 hours"),
    ("P25", "Stage 3: first steps", "Follow the Open_Duck_Mini_Runtime setup, find joint offsets, then run the walk policy on a soft floor with a hand ready to catch.", "P24", "4-8 hours"),
    ("P26", "Stage 3: robot head on the duck", "Mount the shell, face display and camera on top. Keep added mass under about 150 g and centred; re-check walking.", "P25", "4-8 hours"),
    ("P27", "Stage 4: arm and 3-finger hand", "Print the 4-servo arm and tendon hand. Run sim/bench.py with your real masses before printing. Test the arm clamped to the bench first.", "P26", "10-15 hours"),
    ("P28", "Stage 4: squat-and-reach", "Program the squat, reach, grip and lift sequence (the sandbox shows the steps). Test it standing still before trying it while walking.", "P27", "6-10 hours"),
    ("P29", "Stage 4: retrain walking with the arm", "Copy open_duck_mini_v2 in the Playground, add the arm and hand mass, train, and test in MuJoCo before the robot.", "P27", "1-2 days (GPU)"),
    ("P30", "Stage 5: Pi 5, microphone and speaker", "Swap the brain to a Pi 5. Add an I2S amp and speaker and a USB microphone. Test speech in and out with the robot standing still.", "P28", "4-6 hours"),
    ("P31", "Stage 5: voice commands", "Map spoken requests to the same commands the sandbox uses (pick red, place blue, go to pad). Always obey 'stop' first.", "P30", "6-10 hours"),
    ("P32", "Stage 5: first autonomous task", "Tidy-up: find coloured blocks with the camera, carry each to its bin. Run it in the sandbox until it never fails, then on the real floor.", "P31", "Variable"),
]

PARTS = [
    ("U01", "Raspberry Pi Zero 2 W x 1", "Stage 2 brain for video, walking policy and bus servos. 65 x 30 mm.", 25, 35, "Stage 2", "https://core-electronics.com.au/raspberry-pi-zero-2-w-wireless.html"),
    ("U02", "N20 6V 1:298 motors with hall encoders x 4", "Replaces E04 if bought before stage 1. Check shaft and connector.", 40, 80, "Stage 1-2", "https://www.amazon.com.au/s?k=N20+encoder+gear+motor+6V"),
    ("U03", "Track panels and 44 mm sprockets", "Replaces O01. Print or buy; must match motor shaft.", 20, 60, "Stage 2", "https://www.printables.com/search/models?q=robot%20track"),
    ("U04", "Feetech STS3215 servos x 10 (legs)", "Open Duck Mini v2 legs. Order a spare or two.", 250, 400, "Stage 3", "https://github.com/apirrone/Open_Duck_Mini"),
    ("U05", "Feetech bus servo driver board", "USB to serial bus board for the Pi.", 15, 30, "Stage 3", "https://www.feetechrc.com/"),
    ("U06", "BNO055 IMU", "Absolute orientation sensor used by Open Duck.", 35, 55, "Stage 3", "https://core-electronics.com.au/search.php?search_query=BNO055"),
    ("U07", "2S 7.4 V battery with BMS + charger", "18650 2S pack or 2S LiPo 2200 mAh. Charge supervised, in a LiPo bag.", 45, 90, "Stage 3", "https://www.jaycar.com.au/search?text=7.4V+battery"),
    ("U08", "5 V 3 A buck converter, fuse, switch", "Clean supply for the Pi from the 2S pack.", 15, 30, "Stage 3", "https://core-electronics.com.au/search.php?search_query=buck+converter+5V+3A"),
    ("U09", "Feetech STS3215 servos x 4 (arm)", "Yaw, shoulder, elbow, wrist.", 100, 160, "Stage 4", "https://www.feetechrc.com/"),
    ("U10", "3-finger tendon hand (2 micro servos + printed parts)", "About 45 g. Fishing line tendons, elastic return.", 15, 30, "Stage 4", "https://www.printables.com/search/models?q=robot%20hand%20tendon"),
    ("U11", "Raspberry Pi 5 (4 GB) + cooler", "Stage 5 brain for speech and vision.", 95, 125, "Stage 5", "https://core-electronics.com.au/raspberry-pi-5-model-b-4gb.html"),
    ("U12", "I2S amp (MAX98357), speaker, USB microphone", "Voice in and out.", 20, 40, "Stage 5", "https://core-electronics.com.au/search.php?search_query=MAX98357"),
    ("O04", "Pollen Amazing Hand (optional): 8x Feetech SCS0009 + printed parts", "Free print files and code from Pollen (third_party/pollen). About 400 g: too heavy for the walker, use on a bench arm.", 300, 380, "Optional", "https://github.com/pollen-robotics/AmazingHand"),
]

SOFTWARE = [
    (10, "hal.py", "Same code in twin and robot", "Small classes Motor, Servo, Distance, Imu with the same methods in the sandbox, in MuJoCo and on the robot. Behaviours only talk to these.", "A behaviour runs unchanged in sim and on the robot.", "sandbox/model.js, sim/robot_xml.py", "Not started"),
    (11, "link.py (Pi <-> Pico)", "Stage 2 two-brain link", "JSON lines over UART: the Pi sends drive and face commands, the Pico replies with sensor readings. The Pico still stops on its own if messages stop.", "Unplugging the Pi stops the robot within 0.5 s.", "https://docs.micropython.org/en/latest/library/machine.UART.html", "Not started"),
    (12, "walk (Open Duck runtime)", "Walking", "Use Open_Duck_Mini_Runtime unchanged first. Wrap it so hal.py can ask for 'walk at speed v, turn w'.", "Robot walks forward, turns and stops on command.", "https://github.com/apirrone/Open_Duck_Mini_Runtime", "Not started"),
    (13, "arm.py", "Squat, reach, grip, lift", "Two-link IK as in the sandbox; plan squat depth from target height. Check servo load readings and stop if over 80%.", "Picks a 30 mm block from the floor 9 times out of 10.", "sandbox/index.html (planReach, solveArm)", "Not started"),
    (14, "voice.py", "Listen and talk", "Start from Pollen's Reachy Mini conversation app (third_party/fetch_pollen.sh). Speech goes to the same command parser as the sandbox. 'Stop' always wins.", "Understands 'pick up the red block' and 'stop'.", "https://github.com/pollen-robotics/reachy_mini", "Not started"),
    (15, "tasks.py", "Do jobs alone", "Tidy-up: find blocks by colour with the camera, then pick and place each one. Develop it in the sandbox first.", "Finishes the sandbox Tidy-up mission, then the real one.", "sandbox mission 8", "Not started"),
]

WIRING = [
    ("Pi Zero 2 W link", "UART TX/RX/GND to Pico", "Pico UART0 pins, Pi GPIO14/15", "5 V buck for Pi, common ground", "Send a test message each way", "Messages arrive; stop works when unplugged", None, "Not tested"),
    ("Bus servos", "Data line via bus driver board", "Pi USB", "2S 7.4 V through fuse", "One servo at a time: set ID, move 10 degrees", "Correct ID, position read back", None, "Not tested"),
    ("IMU (BNO055)", "I2C SDA/SCL", "Pi I2C", "3.3 V", "Tilt the robot by hand", "Angles follow the tilt", None, "Not tested"),
    ("2S battery + BMS", "Main power", "Switch and fuse", "7.4 V nominal, 8.4 V full", "Measure voltage, then power one servo", "No resets or brown-outs", None, "Not tested"),
    ("Arm and hand", "Bus servos 11-14 + hand servos", "Bus driver board", "7.4 V servos, 5 V micro servos", "Arm clamped on the bench, hold horizontal with block", "Load under 70% of stall, no buzzing", None, "Not tested"),
]


def main():
    wb = openpyxl.load_workbook(SRC)

    # ---- Review sheet (first) ----
    rv = wb.create_sheet("Review v2", 0)
    title(rv, "PLAN REVIEW AND ADAPTATIONS (v2)", "Review of the original plan, adding a walking body, a hand and a voice. Orange rows on other sheets are new in v2.")
    rv["A3"], rv["B3"] = "How to use", "Try designs in sandbox/index.html first, check them with python sim/bench.py, then follow the stage tasks P19-P32 on Project Plan."
    rv["A3"].font = Font(bold=True, color=NAVY)
    rv.merge_cells("B3:F3")
    header(rv, 5, ["Type", "Topic", "Finding", "Change in v2"])
    rows(rv, 6, [(a, b, c, d) for a, b, c, d in REVIEW])
    widths(rv, {"A": 10, "B": 40, "C": 80, "D": 48})
    rv.freeze_panes = "A6"

    # ---- Roadmap sheet ----
    rm = wb.create_sheet("Evolution Roadmap", 2)
    title(rm, "EVOLUTION ROADMAP", "Each stage keeps the last one working. Mass and AUD come from the sandbox design model (planning estimates).")
    header(rm, 4, ["Stage", "Name", "What it adds", "Brain", "Moves on", "New abilities", "Gate test before moving on", "Mass", "Parts AUD"])
    rows(rm, 5, ROADMAP)
    widths(rm, {"A": 8, "B": 14, "C": 60, "D": 20, "E": 14, "F": 32, "G": 44, "H": 12, "I": 12})
    rm.freeze_panes = "A5"

    # ---- Project plan: fixes and new tasks ----
    pp = wb["Project Plan"]
    for r in range(10, pp.max_row + 1):
        if pp.cell(r, 1).value == "P04":
            pp.cell(r, 4).value = "None (v2: start while parts ship)"
            pp.cell(r, 4).fill = PatternFill("solid", fgColor=NEW)
        if pp.cell(r, 1).value == "P18":
            pp.cell(r, 3).value = (pp.cell(r, 3).value or "") + " v2: done in stage 2 with a Pi Zero 2 W (P19-P20)."
            pp.cell(r, 3).fill = PatternFill("solid", fgColor=NEW)
    start = pp.max_row + 2
    section(pp, start, "v2: evolution stages (see Evolution Roadmap)", 6)
    end = rows(pp, start + 1, [t + ("Not started",) for t in TASKS], fill=NEW)
    dv = DataValidation(type="list", formula1=STATUS, allow_blank=False)
    pp.add_data_validation(dv)
    dv.add(f"F{start + 1}:F{end - 1}")

    # ---- Parts: later-stage block ----
    pc = wb["Parts & Costs"]
    start = pc.max_row + 2
    section(pc, start, "v2: parts for later stages (buy each stage only after the one before works)", 10)
    header_row = start + 1
    for c in range(1, 11):
        src = pc.cell(4, c)
        dst = pc.cell(header_row, c, src.value)
        dst.font, dst.fill, dst.border, dst.alignment = copy(src.font), copy(src.fill), copy(src.border), copy(src.alignment)
    pc.cell(header_row, 8).value = "Stage"
    first = header_row + 1
    data = [(i, n, w, lo, hi, None, link, st, "No", "No") for i, n, w, lo, hi, st, link in PARTS]
    last = rows(pc, first, data, fill=NEW) - 1
    for r in range(first, last + 1):
        pc.cell(r, 6).value = f"=D{r}"
        for c in (4, 5, 6):
            pc.cell(r, c).number_format = '"$"#,##0.00'
    tot = last + 1
    pc.cell(tot, 2, "Later stages, excluding optional items").font = Font(bold=True)
    for c, col in ((4, "D"), (5, "E"), (6, "F")):
        cell = pc.cell(tot, c, f'=SUMIF(H{first}:H{last},"<>Optional",{col}{first}:{col}{last})')
        cell.font, cell.number_format = Font(bold=True), '"$"#,##0.00'
        cell.fill = PatternFill("solid", fgColor="00DDEBF0")
    dv2 = DataValidation(type="list", formula1='"No,Yes"', allow_blank=False)
    pc.add_data_validation(dv2)
    dv2.add(f"I{first}:J{last}")

    # ---- Software and wiring ----
    sp = wb["Software Plan"]
    s0 = sp.max_row + 1
    e = rows(sp, s0, SOFTWARE, fill=NEW)
    dv3 = DataValidation(type="list", formula1=STATUS, allow_blank=False)
    sp.add_data_validation(dv3)
    dv3.add(f"G{s0}:G{e - 1}")
    wl = wb["Wiring & Test Log"]
    w0 = wl.max_row + 1
    e = rows(wl, w0, WIRING, fill=NEW)
    dv4 = DataValidation(type="list", formula1='"Not tested,Pass,Fail,Retest"', allow_blank=False)
    wl.add_data_validation(dv4)
    dv4.add(f"H{w0}:H{e - 1}")

    # ---- Sandbox results ----
    sr = wb.create_sheet("Sandbox Results")
    title(sr, "DIGITAL TWIN RESULTS", "From python sim/bench.py sim/designs/*.json (MuJoCo physics). Re-run after every design change.")
    header(sr, 4, ["Design", "Moves on", "Mass (g)", "Top speed (m/s)", "Steepest ramp (deg)", "Tallest step (mm)",
                   "Stands / squats", "Knee peak (% stall)", "Arm out: shoulder load", "Arm out: body tilt (deg)", "Verdict"])
    res = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    out = []
    for r in res:
        arm = r.get("arm") or {}
        legs = "stand_ok" in r
        verdict = []
        if "max_step_mm" in r and r["max_step_mm"] < 20:
            verdict.append(f"steps only {r['max_step_mm']} mm")
        if legs and r["squat_knee_load"] >= 0.9:
            verdict.append("knees at stall")
        if arm and arm.get("tips"):
            verdict.append("tips over with arm out")
        if arm and arm.get("shoulder_load", 0) >= 0.9:
            verdict.append("shoulder near stall")
        out.append((r["name"], r["locomotion"], r["mass_g"], r.get("top_speed_mps"), r.get("max_ramp_deg"), r.get("max_step_mm"),
                    ("yes / yes" if r["stand_ok"] and r["squat_ok"] else "check") if legs else None,
                    round(r["squat_knee_load"] * 100) if legs else None,
                    f"{round(arm['shoulder_load'] * 100)}%" if arm else None,
                    arm.get("body_tilt_deg") if arm else None,
                    "OK" if not verdict else "; ".join(verdict)))
    rows(sr, 5, out)
    widths(sr, {"A": 30, "B": 10, "C": 10, "D": 12, "E": 12, "F": 12, "G": 14, "H": 12, "I": 14, "J": 14, "K": 40})
    sr.freeze_panes = "A5"

    wb.active = 0
    wb.save(DST)
    print("wrote", DST)


if __name__ == "__main__":
    main()
