// Robot design model: turns a robot design (config) into mass, cost, speed,
// runtime, strength checks and a list of abilities. Pure functions, no DOM,
// so the browser sandbox and the Python test bench (via node) share one model.
// These are first-order hand calculations to compare designs, not a substitute
// for the MuJoCo physics tests in sim/ or for testing real parts.
(function (root) {
  "use strict";
  var G = 9.81;

  var STAGES = [
    {
      id: 1, name: "Hatchling", blurb: "The original plan: wheels, Pico W, animated eyes, obstacle sensor.",
      config: { body_mm: 120, height_mm: 80, locomotion: "wheels", drive_motor: "n20_100rpm", wheel_mm: 34,
        leg_servo: "sts3215", leg_mm: 160, arm: false, arm_servo: "mg90s", arm_mm: [60, 55], hand: "gripper2",
        brain: "pico_w", battery: "aa4_nimh", voice: false, mast_mm: 20, payload_g: 20 }
    },
    {
      id: 2, name: "Explorer", blurb: "Track panels on bigger 44 mm sprockets for grip and kerbs, and a Pi Zero 2 W so the camera can stream.",
      config: { body_mm: 120, height_mm: 80, locomotion: "tracks", drive_motor: "n20_100rpm", wheel_mm: 44,
        leg_servo: "sts3215", leg_mm: 160, arm: false, arm_servo: "mg90s", arm_mm: [60, 55], hand: "gripper2",
        brain: "pi_zero_2w", battery: "li18650_2s", voice: false, mast_mm: 30, payload_g: 20 }
    },
    {
      id: 3, name: "Duckling", blurb: "Grows two Open Duck style legs: 10 bus servos, an IMU and a bigger body.",
      config: { body_mm: 170, height_mm: 95, locomotion: "legs", drive_motor: "n20_100rpm", wheel_mm: 34,
        leg_servo: "sts3215", leg_mm: 170, arm: false, arm_servo: "sts3215", arm_mm: [90, 80], hand: "gripper2",
        brain: "pi_zero_2w", battery: "lipo2s_2200", voice: false, mast_mm: 30, payload_g: 20 }
    },
    {
      id: 4, name: "Helper", blurb: "Adds an arm and a small humanoid hand that can carry blocks to bins.",
      config: { body_mm: 170, height_mm: 95, locomotion: "legs", drive_motor: "n20_100rpm", wheel_mm: 34,
        leg_servo: "sts3215", leg_mm: 170, arm: true, arm_servo: "sts3215", arm_mm: [90, 80], hand: "micro_hand",
        brain: "pi_zero_2w", battery: "lipo2s_2200", voice: false, mast_mm: 30, payload_g: 20 }
    },
    {
      id: 5, name: "Companion", blurb: "Pi 5 brain, microphone and speaker. Talks, listens and runs tasks.",
      config: { body_mm: 180, height_mm: 100, locomotion: "legs", drive_motor: "n20_100rpm", wheel_mm: 34,
        leg_servo: "sts3215", leg_mm: 180, arm: true, arm_servo: "sts3215", arm_mm: [90, 80], hand: "micro_hand",
        brain: "pi5_4gb", battery: "li18650_2s", voice: true, mast_mm: 40, payload_g: 20 }
    }
  ];

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function grade(ratio) { return ratio >= 1.5 ? "pass" : ratio >= 1.0 ? "warn" : "fail"; }

  function handLength(hand) { return hand === "amazing_hand" ? 185 : hand === "micro_hand" ? 50 : 35; }

  // Geometry the 3D view and physics bench also use, in millimetres.
  function geometry(cfg) {
    var w = cfg.body_mm, h = cfg.height_mm, wr = cfg.wheel_mm / 2;
    var g = { body_w: w, body_h: h, wheel_r: wr };
    if (cfg.locomotion === "legs") {
      g.crouch_deg = 22;
      g.thigh = cfg.leg_mm / 2; g.shin = cfg.leg_mm / 2;
      g.foot_len = Math.max(40, cfg.leg_mm * 0.45);
      g.hip_spread = w * 0.26;
      g.body_bottom = cfg.leg_mm * Math.cos(g.crouch_deg * Math.PI / 180) + 8;
      g.support_half = g.foot_len / 2;
      g.step_mm = Math.round(cfg.leg_mm * 0.16);
    } else if (cfg.locomotion === "tracks") {
      g.body_bottom = wr * 0.7;
      g.support_half = w * 0.45;
      g.step_mm = Math.round(Math.min(wr * 1.4, g.body_bottom + wr * 0.3));
    } else {
      g.body_bottom = wr * 0.6;
      g.support_half = w * 0.38;
      g.step_mm = Math.round(Math.min(wr * 0.55, g.body_bottom));
    }
    g.arm_mount_x = w * 0.25;             // forward of body centre
    g.arm_mount_z = g.body_bottom + h * 0.85;
    g.hand_len = handLength(cfg.hand);
    return g;
  }

  function evaluate(cfg, P) {
    var C = P.constants, F = P.fixed;
    var brain = P.brains[cfg.brain], batt = P.batteries[cfg.battery];
    var geo = geometry(cfg);
    var parts = [];   // {label, mass, aud:[lo,hi], watts}
    function add(label, mass, aud, watts) { parts.push({ label: label, mass: mass, aud: aud || [0, 0], watts: watts || 0 }); }

    var w = cfg.body_mm, h = cfg.height_mm;
    var shellArea = 2 * w * w + 4 * w * h;
    var shellMass = shellArea * C.shell_wall_mm * C.pla_density_g_cm3 / 1000 * C.shell_fill_factor;
    add("3D printed shell (" + w + " mm)", Math.round(shellMass), [20, 50]);
    add(brain.label, brain.mass, brain.aud, brain.watts);
    add(batt.label, batt.mass, batt.aud);
    add(F.display.label, F.display.mass, F.display.aud, F.display.watts);
    add(F.tof_sensor.label, F.tof_sensor.mass, F.tof_sensor.aud, F.tof_sensor.watts);
    add(F.cam_servo.label, F.cam_servo.mass, F.cam_servo.aud, F.cam_servo.watts);
    add(F.wiring.label, F.wiring.mass, F.wiring.aud, F.wiring.watts);
    if (brain.video) add(F.camera.label, F.camera.mass, F.camera.aud, F.camera.watts);
    if (cfg.voice) add(F.voice_kit.label, F.voice_kit.mass, F.voice_kit.aud, F.voice_kit.watts);

    var motor = P.drive_motors[cfg.drive_motor], servo = P.servos[cfg.leg_servo];
    var nLegServos = 10;
    if (cfg.locomotion === "legs") {
      add(nLegServos + "x " + servo.label + " (legs)", nLegServos * servo.mass,
        [nLegServos * servo.aud_each[0], nLegServos * servo.aud_each[1]]);
      add("Printed legs and feet", Math.round(2 * cfg.leg_mm * 0.18), [5, 15]);
      add(F.imu.label, F.imu.mass, F.imu.aud, F.imu.watts);
      if (servo.feedback) add(F.bus_board.label, F.bus_board.mass, F.bus_board.aud, F.bus_board.watts);
    } else {
      add("4x " + motor.label, 4 * motor.mass, [4 * motor.aud_each[0], 4 * motor.aud_each[1]]);
      add("4x wheels", 4 * F.wheel.mass, [4 * F.wheel.aud_each[0], 4 * F.wheel.aud_each[1]]);
      if (cfg.locomotion === "tracks") add(F.track_set.label, F.track_set.mass, F.track_set.aud);
    }

    var armServo = P.servos[cfg.arm_servo], hand = P.hands[cfg.hand];
    var L1 = cfg.arm_mm[0], L2 = cfg.arm_mm[1], linkMass = 0, armMassTotal = 0;
    if (cfg.arm) {
      linkMass = Math.round((L1 + L2) * 0.12);
      add("4x " + armServo.label + " (arm)", 4 * armServo.mass, [4 * armServo.aud_each[0], 4 * armServo.aud_each[1]]);
      add("Printed arm links", linkMass, [3, 10]);
      add(hand.label, hand.mass, hand.aud);
      if (armServo.feedback && !(cfg.locomotion === "legs" && servo.feedback)) add(F.bus_board.label + " (arm)", F.bus_board.mass, F.bus_board.aud);
      armMassTotal = 4 * armServo.mass + linkMass + hand.mass;
    }

    var massG = parts.reduce(function (s, p) { return s + p.mass; }, 0);
    var M = massG / 1000;
    var cost = parts.reduce(function (s, p) { return [s[0] + p.aud[0], s[1] + p.aud[1]]; }, [0, 0]);
    var checks = [];

    // Locomotion strength and speed
    var speed = 0, locoOk = false, locoWatts = 0;
    if (cfg.locomotion === "legs") {
      var leg_m = cfg.leg_mm / 1000;
      var tNeed = M * G * C.leg_moment_arm_factor * leg_m * C.leg_dynamic_factor;
      var tHave = servo.stall_nm * C.servo_usable_fraction;
      var r = tHave / tNeed;
      checks.push({ id: "knee", label: "Knee servo strength", status: grade(r), ratio: r,
        detail: "Needs " + tNeed.toFixed(2) + " N·m while walking, " + servo.label + " gives about " + tHave.toFixed(2) + " N·m safely." });
      var fits = servo.mass > 30 ? (cfg.body_mm >= 160 && cfg.leg_mm >= 140) : (cfg.body_mm >= 100 && cfg.leg_mm >= 80);
      checks.push({ id: "fit", label: "Leg servos fit the body", status: fits ? "pass" : "fail", ratio: fits ? 2 : 0,
        detail: fits ? "Ten servos fit in this body and leg length." :
          (servo.mass > 30 ? "STS3215 servos are about 45 x 25 x 35 mm. Use a body of at least 160 mm and legs of at least 140 mm."
            : "Use a body of at least 100 mm and legs of at least 80 mm.") });
      checks.push({ id: "feedback", label: "Servos report their position", status: servo.feedback ? "pass" : "fail", ratio: servo.feedback ? 2 : 0,
        detail: servo.feedback ? "Bus servos send joint angles back, which a learned walking policy needs."
          : "Hobby PWM servos cannot report their angle, so the Open Duck walking policy cannot use them." });
      checks.push({ id: "brain_walk", label: "Brain can run a walking policy", status: brain.rl_policy ? "pass" : "fail", ratio: brain.rl_policy ? 2 : 0,
        detail: brain.rl_policy ? brain.label + " can run the Open Duck runtime." : "The Pico W cannot run the neural-network walking policy. Use a Pi Zero 2 W or Pi 5." });
      locoOk = r >= 1 && fits && servo.feedback && brain.rl_policy;
      speed = locoOk ? 0.75 * leg_m : 0;
      locoWatts = nLegServos * servo.watts_active * 0.6;
    } else {
      var rw = cfg.wheel_mm / 2000, eff = cfg.locomotion === "tracks" ? 0.7 : 1.0;
      var th = C.slope_test_deg * Math.PI / 180;
      var force = M * G * (Math.sin(th) + C.rolling_resistance * Math.cos(th));
      var need = force * rw / 4 / eff, have = motor.stall_nm * C.drive_usable_fraction;
      var rr = have / need;
      checks.push({ id: "drive", label: "Drive motors on a " + C.slope_test_deg + "° ramp", status: grade(rr), ratio: rr,
        detail: "Each motor needs " + (need * 1000).toFixed(1) + " mN·m, " + motor.label + " gives about " + (have * 1000).toFixed(0) + " mN·m continuously." });
      locoOk = rr >= 1;
      speed = locoOk ? motor.rpm / 60 * Math.PI * cfg.wheel_mm / 1000 * 0.85 * (cfg.locomotion === "tracks" ? 0.85 : 1) : 0;
      locoWatts = 3.0 * M * (cfg.locomotion === "tracks" ? 1.4 : 1);
    }

    // Arm, hand and tipping
    var armOk = false, armWatts = 0, tipOk = true;
    if (cfg.arm) {
      var hl = geo.hand_len / 1000, l1 = L1 / 1000, l2 = L2 / 1000;
      var load = (cfg.payload_g + hand.mass) / 1000, sm = armServo.mass / 1000, lk = linkMass / 1000;
      var reach = l1 + l2 + hl / 2;
      var tShoulder = G * (load * reach + sm * l1 + sm * (l1 + l2) + lk * (l1 + l2) / 2);
      var tElbow = G * (load * (l2 + hl / 2) + sm * l2 + lk * l2 / 4);
      var aHave = armServo.stall_nm * C.servo_usable_fraction;
      var rs = aHave / tShoulder, re = aHave / tElbow;
      checks.push({ id: "shoulder", label: "Shoulder holds the arm out straight", status: grade(rs), ratio: rs,
        detail: "Needs " + tShoulder.toFixed(2) + " N·m with a " + cfg.payload_g + " g object, servo gives about " + aHave.toFixed(2) + " N·m." });
      checks.push({ id: "elbow", label: "Elbow strength", status: grade(re), ratio: re,
        detail: "Needs " + tElbow.toFixed(2) + " N·m, servo gives about " + aHave.toFixed(2) + " N·m." });
      // Tipping about the front edge of the support area, arm straight out in front.
      var s = geo.support_half / 1000, mx = geo.arm_mount_x / 1000;
      var rest = (M - armMassTotal / 1000) * G * s;
      var over = G * (load * (mx + reach - s) + sm * 2 * (mx - s) + sm * (mx + l1 - s) + sm * (mx + l1 + l2 - s) + lk * (mx + reach / 2 - s));
      var rt = over > 0 ? rest / over : 9;
      checks.push({ id: "tip", label: "Does not tip over when reaching", status: grade(rt), ratio: rt,
        detail: rt >= 1 ? "The body outweighs the reaching arm by " + rt.toFixed(1) + " times." :
          "The arm and object pull harder than the body can resist, so the robot falls on its face." });
      var fitsObj = hand.max_object_mm >= 30;
      tipOk = rt >= 1;
      armOk = rs >= 1 && re >= 1 && tipOk && fitsObj;
      armWatts = 4 * armServo.watts_active * 0.2;
    }

    var watts = parts.reduce(function (s, p) { return s + p.watts; }, 0) + locoWatts + armWatts;
    var runtime = batt.wh * C.battery_usable_fraction / watts * 60;
    var voltOk = !((cfg.locomotion === "legs" && servo.mass > 30) || (cfg.arm && armServo.mass > 30)) || batt.volts >= 7;
    checks.push({ id: "battery", label: "Battery voltage suits the servos", status: voltOk ? "pass" : "fail", ratio: voltOk ? 2 : 0,
      detail: voltOk ? batt.label + " works with the chosen motors and servos." : "STS3215 servos need about 7.4 V. Use a 2S battery." });
    checks.push({ id: "runtime", label: "Battery life", status: runtime >= 30 ? "pass" : runtime >= 15 ? "warn" : "fail", ratio: runtime / 20,
      detail: "About " + Math.round(runtime) + " minutes of mixed use at " + watts.toFixed(1) + " W average." });

    var why = function (ok, reason) { return { ok: !!ok, reason: ok ? "" : reason }; };
    var abilities = {
      drive: why(cfg.locomotion !== "legs" && locoOk && voltOk, cfg.locomotion === "legs" ? "This design walks instead." : "Motors are too weak for this mass."),
      walk: why(cfg.locomotion === "legs" && locoOk && voltOk, cfg.locomotion !== "legs" ? "Grow legs first (stage 3)." : "Fix the red leg checks first."),
      face: why(true, ""),
      obstacle: why(true, ""),
      video: why(brain.video, "The Pico W cannot stream camera video. Add a Pi Zero 2 W."),
      climb: why(geo.step_mm >= 20 && (locoOk), "Can only climb about " + geo.step_mm + " mm. The step is 20 mm."),
      pick: why(cfg.arm && armOk && voltOk, !cfg.arm ? "No arm fitted yet (stage 4)." : "Fix the red arm checks first."),
      talk: why(cfg.voice && brain.speech !== "beeps", !cfg.voice ? "No microphone or speaker fitted." : "The Pico W can only beep. Upgrade the brain."),
      tasks: why(cfg.arm && armOk && brain.video && voltOk, "Needs a working arm and a camera brain to find objects by itself.")
    };
    return { mass_g: massG, parts: parts, cost_aud: cost, speed_mps: speed, runtime_min: runtime, watts: watts,
      step_mm: geo.step_mm, geometry: geo, checks: checks, abilities: abilities };
  }

  var api = { STAGES: STAGES, evaluate: evaluate, geometry: geometry, clone: clone };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.RobotModel = api;
})(typeof window !== "undefined" ? window : globalThis);
