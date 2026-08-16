# ESP-Miner multi-profile porting plan — S19/S21

Baseline reviewed: `bitaxeorg/ESP-Miner` commit `d3dbcc51d11d33b7579baac8c5b9808a4a112790` (GPL-3.0). Rev A.1 should be added as a new board family with an explicit hashboard-profile layer; it must not masquerade as an existing Bitaxe device.

## Driver readiness

| Hashboard family | ASIC | Driver in reviewed ESP-Miner baseline | Initial work |
|---|---|---|---|
| Legacy S19 / S19 Pro revisions | BM1398 | No | Implement and validate a new ASIC driver before mining |
| S19 / S19 Pro / S19j-class BM1362 revisions | BM1362 | No | Implement and validate a new ASIC driver before mining |
| S19 XP / S19j XP / S19k Pro | BM1366 | Yes | Add one immutable profile per exact SKU/chip count and validate a full chain |
| S21 | BM1368 | Yes | Add the 108-chip profile and a NoPIC startup path that never drives RESET |
| S21 Pro / S21 XP / S21+ | BM1370 | Yes | Add separate profiles for their different chip counts and control paths |

The current enum/driver list is visible in ESP-Miner's [`device_config.h`](https://github.com/bitaxeorg/ESP-Miner/blob/d3dbcc51d11d33b7579baac8c5b9808a4a112790/main/device_config.h). An [ESP-Miner S19 XP issue](https://github.com/bitaxeorg/ESP-Miner/issues/248) provides evidence for one 110-chip BM1366 example, not a universal S19 XP count.

## Board GPIO contract

| Function | GPIO | Required firmware behavior |
|---|---:|---|
| Hashboard RESET command | 1 | Drive only through the independently gated reset buffer and only for profiles that explicitly permit it |
| `HB_RESET_OE_N` | 4 | Pull-up makes reset high-impedance; keep high for every `no_gpio_reset` profile |
| Expansion/test | 5, 6 | Leave high-impedance in Rev A.1 production firmware |
| Hashboard UART/PLUG `/OE` | 7 | Active low; external pull-up; enable only after profile selection |
| `FAN_ARM` | 8 | Active high; external pulldown; assert only after EMC2305 configuration and readback |
| Hashboard I2C switch enable | 9 | Active high; external pulldown; keep low before every `HB_3V3` ramp and until the switched rail is stable |
| Hashboard pin-16 3.3 V enable | 10 | Active high; external pulldown |
| Rail monitor | 11 | ADC; require calibrated, plausible values before mining |
| Hashboard `PLUG` | 12 | Debounce and interpret through the exact-board profile |
| EMC2305 ALERT | 13 | Interrupt plus periodic status polling |
| Hashboard SDA/SCL | 14 / 21 | Dedicated hardware I2C controller |
| ASIC UART TX/RX | 17 / 18 | UART1, 8-N-1; matches the reviewed ESP-Miner pin convention |
| Local EMC2305 SDA/SCL | 47 / 48 | Dedicated hardware I2C controller |

All enable GPIOs must be configured to their safe inactive state before any driver probes a bus.

## Profile schema

Create a compile-time table or signed configuration whose records cannot silently fall back to another model. Each profile needs:

- stable profile ID plus exact accepted label/EEPROM identifiers;
- ASIC model, expected response signature, exact chip count, address stride, and domain topology;
- reset policy such as `legacy_active_low` or `no_gpio_reset`, with timings only where measured;
- initial UART rate, register/baud-change sequence, operating UART rate, and verification transaction;
- I2C device addresses and a proven board-local voltage enable/set/readback/shutdown sequence;
- temperature sensor model, conversion, location, plausible range, stale limit, warning and trip limits;
- conservative starting voltage/frequency and bounded ramp steps;
- required fan count, pulses/revolution, minimum plausible RPM, spin-up time, and tach-stale limit; and
- tested startup, fault, cooldown, and recovery ordering.

Runtime ASIC-ID probing may corroborate a configured profile. It must not guess chip count, reset behavior, voltage protocol, or thermal limits from a family name. A missing, conflicting, or ambiguous identity leaves the unit in diagnostic mode.

## Work packages

1. Add an `chainaxe_reva1` board definition with the GPIO contract above and separate `i2c_local` and `i2c_hashboard` buses.
2. Introduce `hashboard_profile_t` and require an exact profile before any cable driver or pin-16 power is enabled.
3. Wrap the existing ASIC drivers behind profile operations for discover, address, set-baud, configure, submit work, read result, and stop.
4. Add an EMC2305 driver with output-type/polarity setup, four PWM/tach channels, tach-age tracking, ALERT decoding, and register readback before `FAN_ARM`.
5. Add `hashboard_power_ops` for board-local I2C `probe`, `enable`, `set_voltage`, `read_status`, `read_temperatures`, and `shutdown`. Do not emulate absent PSU control.
6. Make one high-priority safety task the sole owner of the hashboard OEs, reset OE, pin-16 enable, `FAN_ARM`, and `mining_allowed`.
7. Harden UART RX into a streaming parser that resynchronizes after partial/corrupt frames, validates length/CRC, and publishes error counters. Full-hashboard cables need stricter fault accounting than local Bitaxe traces.
8. Expose profile ID, detected ID/count, state, latched fault, fan RPM/age, temperature age, local-voltage status, UART errors, and recovery count through the UI/API.
9. Preserve ESP-Miner's GPL-3.0 notices and corresponding-source obligations in every distributed firmware image.

## Safety state machine

| State | Required actions and transition |
|---|---|
| `SAFE_BOOT` | Set `FAN_ARM=0`; pin-16 off; UART/PLUG and I2C switches disabled; reset buffer disabled; no jobs. Fan PWM drains float so compatible fans request full speed. |
| `LOCAL_CHECK` | Initialize local I2C, configure EMC2305 for the proven output polarity/mode, command 100%, read registers back, then assert `FAN_ARM`. Require plausible fresh tach from every required fan after spin-up. |
| `PROFILE_SELECT` | Require a configured exact SKU/profile, stable plug state, matching identity evidence, and no latched fault. Unknown or conflicting boards stop here. |
| `HB_IO_START` | Hold `HB_I2C_EN=0`; enable the gated pin-16 3.3 V rail; wait and verify it; then enable the TMUX1511 I2C paths and UART/PLUG paths in the selected profile's order. Reset remains high-impedance unless the profile later requests it. |
| `LOCAL_POWER_CHECK` | Probe the profile's hashboard-local controller/sensors; confirm safe voltage and fresh temperature data. If a local enable command is required, use only the proven per-profile sequence. |
| `ASIC_START` | For a legacy-reset profile, briefly enable the reset buffer and run its measured reset sequence. For S21 NoPIC, never enable the reset buffer and proceed with the bus-only initialization sequence. |
| `ENUMERATE` | Start at the profile's initial baud (normally 115200), enumerate valid responses, and require the exact expected count/IDs before address or clock changes. |
| `CONFIGURE` | Assign addresses, apply the exact ASIC register order, transmit the baud-change command at the old rate, wait for TX completion, switch the ESP UART, and prove the new link before ramping. |
| `MINING` | Accept work only while fan, temperature, plug, rail, identity/count, local-control, and UART-health interlocks remain current and valid. Ramp from a conservative voltage/frequency in bounded steps. |
| `FAULT_LATCHED` | Stop jobs; execute the tested board-local voltage-off/shutdown command if available; deassert the I2C switch before turning off `HB_3V3`; disable other cable paths in the profile-defined safe order; leave S21 reset untouched; release `FAN_ARM` for full-speed cooling; latch cause. |
| `RECOVERY` | Allow at most one conservative retry only for explicitly recoverable faults after a complete cooldown and healthy telemetry interval. Repeated or shutdown-path faults require manual acknowledgement and external power removal. |

An ESP reset or watchdog event must return to `SAFE_BOOT` through physical pulls before application code runs.

## Reset and UART rules

The S21/BM1368 path is a first-class special case, not a timing variation. The public [DCENT_OS S21 profile](https://github.com/DCentralTech/DCENT_OS/blob/main/DCENT_OS_Antminer/dcentrald/dcentrald-silicon-profiles/src/bm1368.rs) identifies a NoPIC design and warns that GPIO-resetting the chains kills the TAS5782M DAC voltage. Therefore an S21 profile keeps GPIO4 high and the reset buffer high-impedance from boot through fault handling.

Bring-up starts at 115200 unless an exact profile proves otherwise. The reviewed ESP-Miner drivers commonly transition newer ASICs to 1 Mbaud, while the public Bitmain-derived S21 profile records 3.125 Mbaud operation. Treat operating baud as profile data: send the ASIC baud command while the ESP is still at the old rate, wait for TX completion, switch the local UART, and validate register reads before accepting work. Do not select the faster number merely because the chip family can support it.

## Fault policy without PSU control

Rev A.1 has no means to disconnect the external hashboard core-power bus. Its strongest local response is to stop work, send a previously validated hashboard-local I2C voltage-off/shutdown command, disable cable interfaces where doing so is safe, and force fans to their fail-safe full-speed condition. If temperature rises, the local command NACKs, rail readback remains unsafe, or the board profile has no proven shutdown operation, firmware must display **EXTERNAL POWER REMOVAL REQUIRED** and remain latched. Documentation and UI must never describe this as a guaranteed hard shutdown.

Other mandatory trips:

- missing/stale/implausible fan tach, EMC2305 ALERT, or local-I2C failure;
- stale/invalid temperature data or a profile-specific overtemperature;
- plug removal, hashboard-I2C failure, unexpected chip count/ID, CRC/framing storm, or failed baud verification;
- brownout or watchdog reset; and
- an attempted profile change while any hashboard interface is enabled.

Network/pool loss is not a reason to disable cooling. Stop issuing work and move to the profile's safe idle state while telemetry continues.

## Validation sequence

### Host tests

- Golden command/response/CRC vectors for every supported ASIC driver.
- Exact address list and count for every profile.
- State-transition tests for every timeout, reset policy, and fault.
- Parser fuzzing with partial, concatenated, corrupted, and shifted frames.
- EMC2305 polarity, tach/RPM conversion, stale-age, ALERT, `FAN_ARM`, and watchdog tests.
- Assert in tests that `no_gpio_reset` profiles can never lower GPIO4 or drive GPIO1 onto the cable.

### Controller-only HIL

- Record all enable pins during power-on, flashing, brownout, watchdog, and software reset.
- Confirm USB cannot backfeed J1, J6, fan motor power, or J10 pin 16.
- Exercise four real fans; unplug and stall each independently; verify floating PWM produces full speed.
- Verify J1 only receives regulated 12 V and J6 operates over 12–15 V.
- Short each I2C line through a safe resistor and prove mining cannot become allowed.

### Unpowered / locally powered hashboard

- Confirm connector orientation, common ground, 3.3 V signal levels, PLUG polarity, I2C devices, and pin-16 current with a scope/current limit.
- On S21, prove RESET remains high-impedance during every boot and fault transition.
- Validate the board-local voltage/temperature controller and safe shutdown command without enabling mining.

### Low-power full-chain test

- Enumerate the exact profile count at 115200 on at least 100 cold boots.
- Validate address assignment and the selected operating rate with no persistent CRC/framing faults.
- Start at the profile's conservative voltage/frequency; compare current, temperatures, and response rate with known-good controller behavior.

### Mining and fault injection

- Submit known jobs and verify accepted nonces/shares.
- Inject fan stall, cable removal, stale temperature, I2C NACK, UART corruption, local-voltage-control failure, brownout, and ESP watchdog.
- Verify prompt job stop, the local shutdown request when supported, full-speed fan fallback, latched UI warning, and the explicit external-disconnect requirement when core power remains.
- Complete a 24-hour conservative soak before any ramp increase; log UART errors, minimum fan RPM, temperatures, resets, local rail state, and accepted/rejected shares.

## Release blockers

- Exact first hashboard SKU/revision, verified chip count/domain map, and readable identity method.
- Exact reset policy and proof that S21 NoPIC never sees a driven reset.
- Exact board-local voltage, temperature, enable, readback, and shutdown protocol.
- Tested initial/operating baud and complete initialization register order.
- Exact fans, current/inrush, pulses/revolution, minimum safe RPM, and connector orientation.
- Sensor calibration and conservative voltage/frequency/temperature envelope.
- Clear operator procedure or independent hardware protection for removal of external core power.

Until these are closed, firmware remains a supervised bench/enumeration build and must not permit unattended mining.
