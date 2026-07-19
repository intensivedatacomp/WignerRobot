# WignerRobot

A client/server framework for remotely driving a Raspberry Pi–based robot car from a PC, with a live low‑latency video feed, keyboard-based motion and camera-gimbal control, an ultrasonic distance sensor, a buzzer for playing songs, and an 8x16 dot-matrix display.

The PC runs a Tkinter **control center** that renders the robot's video stream and sends control commands over the network. The Raspberry Pi runs a **robot client** that drives the motors/servos/sensors and streams its camera feed back, using `ffmpeg` for hardware-accelerated H.264 encoding/decoding over UDP.

## Features

- 🎮 **Keyboard teleoperation** — drive, steer, and brake the robot with arrow keys
- 📷 **Live video streaming** — low-latency H.264 stream over UDP, decoded and rendered in a desktop GUI
- 🎯 **Camera & sensor gimbal control** — pan/tilt the camera and ultrasonic sensor with dedicated keys
- 📡 **Ultrasonic distance sensing** — toggleable obstacle-distance measurement
- 🔊 **Buzzer songs** — play built-in tunes (or add your own) defined in `songs.json`
- 💡 **Dot-matrix display** — show icons/expressions on an 8x16 LED matrix, defined in `dot_matrices.json`
- 🔌 **Automatic encoder fallback** — tries hardware encoders (NVENC, QSV, AMF) before falling back to software `libx264`
- 🧵 **Threaded, non-blocking control loop** — motors, servos, sensor, and buzzer each run on their own background thread

## Architecture

```
┌─────────────────────────────┐        TCP (control)        ┌─────────────────────────────────┐
│         PC / Server         │ ───────────────────────────▶│        Raspberry Pi             │
│                             │        JSON state           │          (Robot)                │
│  controlCenter.py (Tk GUI)  │ ◀───────────────────────────│       robotClient.py            │
│   ├─ ControlServer          │        UDP (video, H.264)   │        ├─ ControlClient         │
│   ├─ VideoServer (ffmpeg)   │ ◀───────────────────────────│        ├─ VideoClient (ffmpeg)  │
│   └─ keybindings.py         │                             │        ├─ Motor                 │
└─────────────────────────────┘                             │        ├─ Servo                 │
                                                            │        ├─ USSensor              │
                                                            │        ├─ Buzzer                │
                                                            │        └─ DotMatrix             │
                                                            └─────────────────────────────────┘
```

The control server pushes the full desired robot state (speed, servo angles, sensor toggle, buzzer song, shutdown flag) to the robot on a fixed interval; the robot client applies it to the hardware and reports back a distance measurement. Video flows one-way from the robot's camera to the PC's display.

## Repository Structure

```
WignerRobot/
├── environment.yml          # Conda environment definition
├── settings.json            # Shared network/robot configuration
├── songs.json                # Buzzer note sequences (frequency, duration)
├── dot_matrices.json        # 8x16 dot-matrix bitmap definitions
├── server/                  # Runs on the PC
│   ├── controlCenter.py     # Entry point: Tkinter GUI, wires everything together
│   ├── controlServer.py     # TCP server pushing control state to the robot
│   ├── videoServer.py       # Receives/decodes the UDP video stream via ffmpeg
│   ├── keybindings.py       # Keyboard → control-state mapping
│   └── control.py           # Shared control-state container
└── robot/                   # Runs on the Raspberry Pi
    ├── robotClient.py        # Entry point: connects to server, drives hardware
    ├── controlClient.py      # TCP client receiving control state
    ├── videoClient.py        # Captures/encodes the camera feed via ffmpeg
    ├── control.py             # Shared control-state container
    └── components/
        ├── motor.py           # 4-wheel differential drive over GPIO/PWM
        ├── servo.py            # Camera pan/tilt + ultrasonic sensor servo
        ├── usSensor.py         # HC-SR04-style ultrasonic distance sensor
        ├── buzzer.py            # PWM buzzer with song playback
        └── dotMatrix.py         # 8x16 LED dot-matrix driver
```

## Requirements

**PC (server):**
- Python 3.12
- [`ffmpeg`](https://ffmpeg.org/) available on `PATH`
- `numpy`, `pillow`, `tk` (see `environment.yml`)

**Raspberry Pi (robot):**
- Python 3.12
- `ffmpeg`
- `RPi.GPIO`
- `opencv-python-headless`
- A camera accessible via OpenCV (`cv2.VideoCapture`)
- Motors, servos, an ultrasonic sensor, a buzzer, and/or a dot-matrix display wired to the GPIO pins used in `robot/components/`

## Installation

Both the PC and the Raspberry Pi use the same conda environment definition.

```bash
git clone https://github.com/<your-org>/WignerRobot.git
cd WignerRobot
conda env create -f environment.yml
conda activate WignerRobot
```

> `RPi.GPIO` is only importable on a Raspberry Pi — the robot-side hardware modules (`motor.py`, `servo.py`, `usSensor.py`, `buzzer.py`, `dotMatrix.py`) will fail to import elsewhere. The server side has no such dependency.

## Configuration

All shared settings live in `settings.json` at the repository root:

| Key | Description |
|---|---|
| `HOST_IP` | IP address of the PC/server (the robot connects to this) |
| `LISTEN_IP` | Interface the server binds to (`0.0.0.0` for all interfaces) |
| `VIDEO_PORT` / `CONTROL_PORT` | UDP video / TCP control port numbers |
| `IMAGE_WIDTH` / `IMAGE_HEIGHT` / `IMAGE_CHANNELS` | Video frame dimensions |
| `FPS` | Target video frame rate |
| `THREAD_SLEEP` | Poll interval for control/hardware threads |
| `TIMEOUT_TIME` | Robot-side socket timeout before treating the connection as lost |
| `MAX_SPEED` / `MIN_SPEED` / `ACCELERATION` | Motor speed limits and step size per key press |
| `DEFAULT_ANGLES` | Default servo angles `[us, horizontal, vertical]` |
| `ANGLE_STEP` | Servo angle change per key press |

Update `HOST_IP` to the PC's IP address on your network before running the robot client.

## Usage

**1. Start the control center on the PC:**

```bash
cd WignerRobot
python server/controlCenter.py
```

This opens a window that waits for the robot to connect and will display its video feed once connected.

**2. Start the robot client on the Raspberry Pi:**

```bash
cd WignerRobot
python robot/robotClient.py
```

The robot connects to `HOST_IP`, starts streaming video, and begins listening for control commands. Click into the control-center window and use the keyboard to drive.

## Controls

| Key(s) | Action |
|---|---|
| `↑` / `↓` | Accelerate forward / backward |
| `←` / `→` | Turn left / right |
| `Space` | Stop and reset servos to default angles |
| `W` / `S` | Tilt camera vertical servo up / down |
| `A` / `D` | Pan camera horizontal servo left / right |
| `O` / `P` | Adjust ultrasonic sensor servo angle |
| `M` | Toggle ultrasonic distance measuring |
| `B` then `V` / `N` / `Y` / `M` | Play a buzzer song (violent / nino / supermario / masiksong) |
| `B` then `B` | Stop the current song |
| `Esc` / `Q` | Shut down the robot connection |

Buzzer songs are defined as `[frequency, duration]` note pairs in `songs.json` — add new entries there to make them available via key combos in `server/keybindings.py`.

## Customization

- **Add a song:** append a new `"name": [[freq, duration], ...]` entry to `songs.json`, then bind a key to it in `server/keybindings.py`.
- **Add a dot-matrix icon:** append a new 16-byte array to `dot_matrices.json` and display it with `DotMatrix.show("name")`.
- **Change video encoders:** `VideoClient` tries encoders in the order given by its `encoders` argument (default: `h264_nvenc`, `h264_qsv`, `h264_amf`, `libx264`), probing each before use and falling back automatically if unavailable.
