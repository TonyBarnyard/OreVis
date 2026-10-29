// Robot parts library: the single source of truth for the browser sandbox
// (sandbox/index.html) and the MuJoCo test bench (sim/parts.py reads this file).
// Everything after "ROBOT_PARTS =" must stay valid JSON.
// Masses, torques and prices are planning estimates. Check the seller's datasheet before buying.
// Torque in N·m, mass in grams, power in watts, prices in AUD (low, high).
window.ROBOT_PARTS = {
  "brains": {
    "pico_w":     {"label": "Raspberry Pi Pico W", "mass": 4,  "watts": 0.4, "aud": [9.5, 18],  "video": false, "bus_servos": false, "rl_policy": false, "speech": "beeps", "note": "Great for motors, face and sensors. Cannot stream video or run a walking policy."},
    "pi_zero_2w": {"label": "Raspberry Pi Zero 2 W", "mass": 11, "watts": 1.5, "aud": [25, 35],   "video": true,  "bus_servos": true,  "rl_policy": true,  "speech": "cloud", "note": "The Open Duck Mini runs its walking policy on this board. Can stream a Pi camera."},
    "pi5_4gb":    {"label": "Raspberry Pi 5 (4 GB)",  "mass": 46, "watts": 5.0, "aud": [95, 115], "video": true,  "bus_servos": true,  "rl_policy": true,  "speech": "local", "note": "Enough for on-board speech recognition, a small vision model and the walking policy together."}
  },
  "drive_motors": {
    "n20_300rpm": {"label": "N20 6V 1:100 (~300 rpm)", "mass": 10, "rpm": 300, "stall_nm": 0.08, "aud_each": [7, 15]},
    "n20_100rpm": {"label": "N20 6V 1:298 (~100 rpm)", "mass": 10, "rpm": 100, "stall_nm": 0.22, "aud_each": [7, 15]},
    "tt_200rpm":  {"label": "TT yellow motor 1:48",    "mass": 30, "rpm": 200, "stall_nm": 0.08, "aud_each": [3, 6]}
  },
  "servos": {
    "sg90":    {"label": "SG90 micro servo",              "mass": 9,  "stall_nm": 0.18, "watts_active": 0.6, "feedback": false, "aud_each": [3, 6]},
    "mg90s":   {"label": "MG90S metal-gear micro servo",   "mass": 14, "stall_nm": 0.21, "watts_active": 0.8, "feedback": false, "aud_each": [5, 9]},
    "scs0009": {"label": "Feetech SCS0009 bus micro servo","mass": 7,  "stall_nm": 0.23, "watts_active": 0.6, "feedback": true,  "aud_each": [8, 14]},
    "sts3215": {"label": "Feetech STS3215 bus servo (7.4 V)","mass": 55, "stall_nm": 1.9, "watts_active": 2.0, "feedback": true,  "aud_each": [25, 40]}
  },
  "hands": {
    "gripper2":     {"label": "2-finger printed gripper (1 servo)",          "mass": 25,  "servos": 1, "fingers": 2, "max_object_mm": 45, "aud": [5, 12],   "note": "Simplest and lightest. Best first hand for the 120 mm body."},
    "micro_hand":   {"label": "3-finger tendon hand (2 micro servos)",       "mass": 45,  "servos": 2, "fingers": 3, "max_object_mm": 50, "aud": [15, 30],  "note": "Humanoid look at small scale. Fingers curl on strings pulled by two servos."},
    "amazing_hand": {"label": "Pollen Amazing Hand (8 servos, 4 fingers)",   "mass": 400, "servos": 8, "fingers": 4, "max_object_mm": 90, "aud": [300, 380], "note": "Open-source humanoid hand, about 400 g. Needs an Open Duck sized body and STS3215 arm servos."}
  },
  "batteries": {
    "aa4_nimh":    {"label": "4x AA NiMH 2000 mAh (4.8 V)", "mass": 115, "volts": 4.8, "wh": 9.6,  "aud": [20, 40]},
    "lipo2s_1000": {"label": "2S LiPo 1000 mAh (7.4 V)",    "mass": 60,  "volts": 7.4, "wh": 7.4,  "aud": [20, 35]},
    "li18650_2s":  {"label": "2x 18650 2S pack (7.4 V)",    "mass": 105, "volts": 7.4, "wh": 18.5, "aud": [30, 55]},
    "lipo2s_2200": {"label": "2S LiPo 2200 mAh (7.4 V)",    "mass": 125, "volts": 7.4, "wh": 16.3, "aud": [30, 50]}
  },
  "fixed": {
    "display":     {"label": "Pico Display Pack 2.0",        "mass": 22, "watts": 0.3, "aud": [30, 45]},
    "tof_sensor":  {"label": "VL53L0X distance sensor",      "mass": 3,  "watts": 0.1, "aud": [10, 25]},
    "cam_servo":   {"label": "Camera tilt servo (SG90)",     "mass": 9,  "watts": 0.2, "aud": [5, 15]},
    "camera":      {"label": "Camera module",                "mass": 5,  "watts": 0.5, "aud": [35, 55]},
    "wiring":      {"label": "Drivers, wiring, screws",      "mass": 35, "watts": 0.1, "aud": [43, 100]},
    "imu":         {"label": "BNO055 IMU (legs only)",       "mass": 4,  "watts": 0.05,"aud": [35, 55]},
    "bus_board":   {"label": "Bus servo driver board",       "mass": 8,  "watts": 0.05,"aud": [15, 30]},
    "voice_kit":   {"label": "Mic + I2S amp + speaker",      "mass": 20, "watts": 0.5, "aud": [20, 40]},
    "wheel":       {"label": "Wheel (each)",                 "mass": 6,  "aud_each": [2.5, 6]},
    "track_set":   {"label": "Track set (pair)",             "mass": 45, "aud": [20, 60]}
  },
  "constants": {
    "pla_density_g_cm3": 1.24,
    "shell_wall_mm": 2.0,
    "shell_fill_factor": 0.8,
    "drive_usable_fraction": 0.3,
    "servo_usable_fraction": 0.5,
    "leg_moment_arm_factor": 0.21,
    "leg_dynamic_factor": 1.5,
    "battery_usable_fraction": 0.8,
    "slope_test_deg": 15,
    "rolling_resistance": 0.05
  }
};
