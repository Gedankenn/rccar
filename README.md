# rccar

ESP32-C3 SuperMini firmware for a small brushed RC car: WiFi AP + browser
joystick, H-bridge drive, hobby servo steering, battery telemetry, and a
400 ms failsafe.

Status: firmware builds for `esp32c3`; hardware not yet wired or tested.
Chassis plan: 2S Li-ion (7.4 V), brushed motor, existing steering servo,
phone browser control.

## Layout

```
main/
  main.c        boot, failsafe task, status LED
  motor.c/.h    brushed motor over LEDC (H-bridge IN1/IN2)
  steering.c/.h servo over LEDC (50 Hz, 1-2 ms)
  battery.c/.h  pack voltage on ADC1
  web.c/.h      SoftAP, HTTP server, WebSocket control, /api/status
  index.html    embedded single-page joystick UI
  config.h      pin map and tuning constants
docs/
  hardware.md   chassis notes, BOM, wiring, ESP32-C3 constraints
  design.md     scope, decisions, open questions
```

## Build

ESP-IDF v5.5, target `esp32c3`, 4 MB flash. Docker keeps the host clean:

```sh
docker run --rm -v "$PWD":/project -w /project espressif/idf:release-v5.5 \
  bash -lc 'idf.py set-target esp32c3 && idf.py build'
```

Output: `build/rccar.bin` (merged image via `idf.py build`).

## Flash and monitor

The SuperMini has native USB (USB-Serial-JTAG on GPIO18/19), so no UART
adapter is needed:

```sh
docker run --rm -it --device /dev/ttyACM0 \
  -v "$PWD":/project -w /project espressif/idf:release-v5.5 \
  bash -lc 'idf.py -p /dev/ttyACM0 flash monitor'
```

If the port does not appear, hold BOOT (GPIO9) while plugging the cable.

## Drive

1. Power the car, wheels off the ground.
2. Join WiFi `rccar-XXXX` (password `rccar1234`).
3. Open <http://192.168.4.1/>.
4. Drag on the pad or use W/A/S/D. Press **ARM** to allow motor output;
   releasing the pointer, hiding the tab, or losing the link stops the motor.
5. `curl http://192.168.4.1/api/status` returns voltage, command, armed state.

## Safety

- Wheels off the ground for every flash and first test.
- Firmware output is disarmed after every new WebSocket client and after
  400 ms without a control frame.
- Below 6.4 V on a 2S pack the drive latches off until reboot (LED fast
  blink, UI shows LOCKED).
- The motor driver's STBY pin goes to 3.3 V in the current wiring plan; add a
  hardware switch in series with the battery for bench work.

## Not done yet

- Hardware bring-up and current measurements (motor and servo).
- Encoder/IMU, OTA, mDNS.
- The pin map assumes an H-bridge on GPIO3/4 and a servo on GPIO5; adjust
  `main/config.h` once the actual board and connectors are known.
