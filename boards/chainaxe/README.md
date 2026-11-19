# chainaxe control board v0.1

ESP32-S3 Antminer hashboard controller. Outline, mounting holes and connector positions follow a
measured drawing of the stock S19 control board (110 x 100 mm, 4 layers; see extra/outline/),
with a BitaxeGT-style ESP32-S3-WROOM-1 in place of the Bitcrane's FTDI USB bridge.

Derived from [skot/bitcrane](https://github.com/skot/bitcrane) and
[bitaxeorg/BitaxeGT](https://github.com/bitaxeorg/BitaxeGT). Licensed CERN-OHL-S-2.0 (see the
LICENSE at the repository root).

## Connectors (same places as the stock S19 control board)

| Ref | What |
|---|---|
| J2 / J9 / J10 | Hashboard 0 / 1 / 2 data cable, Antminer 18-pin 2x9 2.0 mm |
| J4-J7, J14-J17 | Fans 1-4, 2.54 mm 4-pin or 4.2 mm 2x2 (populate one per fan) |
| J3 | 12 V in (6-pin 4.2 mm), reverse-protected by Q1 |
| J1 | Antminer PSU control, 2x3 2.0 mm (I2C + PSU_EN) |
| J11 | USB-C: ESP32-S3 native USB (flashing + console). Does not power the board. |

## ESP32-S3 GPIO map

Three hashboard UARTs: UART0, UART1 and UART2 routed through the GPIO matrix to any pins below.
The console is on USB-Serial-JTAG, so UART0's default pins (GPIO43/44) are left unused.

| Signal | GPIO | Signal | GPIO |
|---|---|---|---|
| HB0 TX | 48 | HB1 TX | 11 |
| HB0 RX | 47 | HB1 RX | 12 |
| HB0 RST | 14 | HB1 RST | 13 |
| HB0 PLUG | 21 | HB1 PLUG | 10 |
| HB2 TX | 39 | I2C SDA | 9 |
| HB2 RX | 40 | I2C SCL | 3 |
| HB2 RST | 41 | | |
| HB2 PLUG | 38 | PSU_EN | 18 |
| BOOT | 0 | USB D-/D+ | 19 / 20 |

| Fan | PWM GPIO (LEDC) | Tach GPIO (PCNT) |
|---|---|---|
| 1 | 15 | 42 |
| 2 | 16 | 44 |
| 3 | 17 | 2 |
| 4 | 8 | 1 |

The I2C bus is shared by the three hashboard headers and the PSU header.

Fans are driven directly: each fan's PWM pin is pulled low by a 2N7002K (Q2-Q5) whose gate the
ESP32 drives with 25 kHz LEDC PWM (inverted: gate high = PWM low). A 100k pull-down holds each gate
off, so with the ESP32 in reset the fans' own pull-ups run them at full speed. Tach lines keep
their 36k pull-ups and reach the ESP32 through 1k series resistors; count them with PCNT
(2 pulses per revolution). The ESP-to-fan lines run on the In2 (3V3 plane) layer.

## Power

12 V -> Q1 reverse protection -> TPSM861253 module -> 3V3 (1 A) on the In2 plane.
Hashboard header pin 16 gets 3V3, as on the Bitcrane.

## Not yet checked on hardware

- Hashboard UARTs are driven straight at 3.3 V, the same as the Bitcrane does from its FTDI.
- Fan PWM pull-ups (R22, R23, R47, R48) go to 3V3 instead of the Bitcrane's 5 V.
- GPIO44 (fan 2 tach) is UART0 RX at boot; harmless as an input.
