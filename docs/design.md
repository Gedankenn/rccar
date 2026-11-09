# rccar - design note

Date: 2026-11-09
Status: draft, assumptions marked, awaiting chassis details.

## Intent

Turn the stripped 1/16 chassis in the photo into a WiFi-controlled car with
an ESP32-C3 SuperMini, without buying a proprietary receiver/ESC combo. The
car should be drivable from a phone browser and be safe when the link drops.

## Goals

- Drive one brushed motor forward/reverse with proportional throttle.
- Steer with one hobby servo.
- Control from a phone: no app install, no extra radio.
- Stop within a fraction of a second when commands stop.
- Report pack voltage.
- Build with stock ESP-IDF, no proprietary blobs beyond Espressif's.

## Non-goals (for v0)

- Racing-grade latency or a real RC transmitter link.
- Brushless motor, sensored control, or telemetry back-channel.
- Autonomous driving, odometry, camera.
- OTA updates, multi-car support, mDNS.

## Anti-goals

- A build that only works on the bench because the loop is blocking.
- Servo or motor power stolen from the SuperMini LDO.
- A UI that can command the motor without an explicit arm step.

## Approaches

1. **ESP-IDF + WiFi SoftAP + WebSocket UI (chosen).** Native C, one binary,
   LEDC for both PWM loads, browser as the controller. No app, no extra
   hardware. Costs WiFi power and a phone in hand.
2. **Arduino/PlatformIO + WiFi UI.** Faster to prototype, but the same
   result with a heavier abstraction layer and worse control over timing;
   the owner works in C and ESP-IDF anyway.
3. **BLE HID gamepad.** Better feel, but needs a BLE-capable pad and more
   pairing work; the C3 has no Bluetooth Classic, so common DualShock pads
   are out. A later addition, not the first link.

Why 1: the C3 has no MCPWM, so precise pulses are not the differentiator;
WiFi + HTTP/WebSocket is well supported, and the browser gives a usable UI
with no client build step.

## Decisions taken (mine, reversible)

- **LEDC for both loads.** Motor at 20 kHz (inaudible, fine for a brushed
  H-bridge), servo at 50 Hz with 14-bit duty (the C3's maximum). RMT stays
  free for a future precise servo or WS2812.
- **Sign-magnitude drive.** IN1 PWM + IN2 low for one direction, swapped for
  the other, both low to coast. Works with TB6612, DRV8833 and DRV8871.
- **Arming is explicit.** A new WebSocket client starts disarmed; only the
  arm flag enables the motor. Steering stays live while disarmed so the
  linkage can be centered.
- **Failsafe at 400 ms.** No control frame, no drive; a tab close or WiFi
  drop stops the car. The UI sends a 20 Hz heartbeat while connected.
- **Voltage divider 100k/47k on GPIO0.** 2S pack fits the ADC range;
  resistor values keep drain under 60 uA.
- **Low-voltage latch at 6.4 V.** Five consecutive samples below the
  threshold disarm the car until reboot; arming is refused in firmware, not
  only hidden in the UI.
- **Dockerized build.** No host-wide ESP-IDF install; the repo builds with
  one command.

## Settled with the owner

- Pack: 2S Li-ion, 7.4 V nominal.
- Steering servo and linkage are already on the chassis.
- First control link: phone browser over WiFi (what is built).

## Open questions (need the owner)

1. Exact motor: can size, winding, connector, stall current. This picks
   TB6612FNG versus DRV8251A.
2. Servo model and rated voltage; confirm it accepts 5 V.
3. Is a physical RC transmitter or BLE gamepad wanted later?

## What is left to the builder

- Confirm the pin map against the real SuperMini board revision.
- Measure stall current before soldering the H-bridge.
- Decide whether STBY gets a GPIO kill line or stays tied to 3.3 V.
- Add a 2S BMS and balance charger to the build.
