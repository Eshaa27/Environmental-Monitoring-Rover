# Autonomous Environmental Monitoring Rover

> A four-wheel rover platform for safe remote driving, local obstacle avoidance, and environmental sensing.

> **Project status:** This is an active, ongoing project. The core control and communication components are in place, while autonomous navigation, environmental intelligence, mapping, and long-range telemetry are under development.

The project combines a desktop control station, a Raspberry Pi communication bridge, and Arduino firmware. Its design keeps time-critical motor and obstacle handling close to the hardware, while the Raspberry Pi connects the rover to the GUI and provides a foundation for navigation, telemetry, and environmental analysis.

## System architecture

```text
┌──────────────────┐       Wi-Fi / TCP       ┌──────────────────┐    USB serial    ┌──────────────────┐
│  Desktop GUI     │ ◀─────────────────────▶ │ Raspberry Pi 4B  │ ◀──────────────▶ │     Arduino      │
│  PySide6         │                         │  rover server    │                  │  motor control   │
└──────────────────┘                         └──────────────────┘                  └───────┬──────────┘
                                                                                             │
                                                                            ┌────────────────┴─────────────────┐
                                                                            │ 4 DC motors · 3 ultrasonic sensors │
                                                                            └──────────────────────────────────┘
```

The Raspberry Pi is the high-level controller. It relays commands between the GUI and Arduino, and is the planned location for IMU processing, environmental sensing, data storage, and navigation. The Arduino drives the motors and enforces near-hardware obstacle safety.

## Current capabilities

- Desktop GUI with manual drive controls, telemetry, system status, and map-oriented controls.
- TCP communication between the GUI and Raspberry Pi bridge.
- JSON-over-serial protocol between the Raspberry Pi and Arduino.
- Four-wheel motor control using an Adafruit Motor Shield V1.
- Front, left, and right ultrasonic sensing for obstacle awareness.
- Manual and autonomous firmware modes, with a command watchdog for manual operation.
- Raspberry Pi sensor-test scaffold for DHT22 temperature/humidity and MQ-5 gas readings through an ADS1115.

## Repository layout

```text
.
├── arduino/
│   └── rover-arduino.ino       # Motor, ultrasonic, and safety firmware
├── desktop-gui/
│   └── LatestGUI.py            # PySide6 control station
├── raspberry-pi/
│   ├── rover_server.py         # TCP-to-serial bridge
│   └── sensor_testing.py       # Environmental-sensor test scaffold
├── .gitignore
└── README.md
```

## Hardware

| Component | Role |
| --- | --- |
| Raspberry Pi 4B | High-level processing and GUI/serial bridge |
| Arduino + Adafruit Motor Shield V1 | Motor control and ultrasonic safety handling |
| 4 DC motors | Rover drivetrain |
| 3 ultrasonic sensors | Front, left, and right obstacle distance sensing |
| DHT22 | Temperature and humidity sensing |
| MQ-5 + ADS1115 | Gas sensing and analogue-to-digital conversion |
| 9-DOF IMU *(planned)* | Heading and motion estimation |
| LoRa module *(planned)* | Long-range, low-bandwidth telemetry and alerts |

## Getting started

### 1. Upload the Arduino firmware

Open [`arduino/rover-arduino.ino`](arduino/rover-arduino.ino) in the Arduino IDE and install:

- **Adafruit Motor Shield V1** (`AFMotor`)
- **ArduinoJson**

Check the pin assignments and tuning constants near the top of the sketch before uploading. The default ultrasonic mapping is:

| Direction | Trigger | Echo |
| --- | --- | --- |
| Front | `A2` | `A3` |
| Left | `A4` | `A5` |
| Right | `A0` | `A1` |

### 2. Start the Raspberry Pi bridge

On the Raspberry Pi, install PySerial and run the bridge:

```bash
python3 -m pip install pyserial
python3 raspberry-pi/rover_server.py
```

The bridge listens on TCP port `5000` and expects the Arduino at `/dev/ttyACM0` at `115200` baud. Update `SERIAL_PORT`, `BAUD`, or `SERVER_PORT` in [`rover_server.py`](raspberry-pi/rover_server.py) if your hardware differs.

### 3. Run the desktop GUI

On the control computer, install PySide6 and start the application:

```bash
python3 -m pip install PySide6
python3 desktop-gui/LatestGUI.py
```

Set `ROVER_HOST` in [`LatestGUI.py`](desktop-gui/LatestGUI.py) to the Raspberry Pi's hostname or IP address. The default is `lorarover.local` on port `5000`.

## Safety notes

- Test with the rover raised from the ground before connecting the motors to a live drivetrain.
- Keep an accessible power disconnect or emergency stop during testing.
- Calibrate the obstacle threshold, speed, and timing constants for the actual chassis and test area.
- Treat GUI position and heading as estimates until a complete localization system is implemented.

## Roadmap

- [ ] IMU-based heading and estimated position tracking
- [ ] Click-to-target map navigation with A* path planning
- [ ] Dynamic obstacle-map updates and route replanning
- [ ] Persistent telemetry and mission-history storage
- [ ] Environmental anomaly detection and spatial hazard mapping
- [ ] Risk-aware route costs using environmental sensor data
- [ ] LoRa telemetry for critical alerts and remote status

## Project vision

The intended end state is more than a rover that follows a shortest path: it is a risk-aware environmental monitoring platform. It will associate sensor readings with estimated location, identify hazardous conditions, visualize them on a map, and choose safer paths when conditions demand it.

## License

No license has been selected yet. Add a license file before distributing or accepting outside contributions.
