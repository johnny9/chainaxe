# PCB start

- `floorplan.svg` is the Rev A.1 visual placement concept.
- `floorplan.png` is a rendered review copy of the same drawing.
- `placement.csv` records the synchronized major-block centers from the Rev A.1 KiCad baseline in a board-relative 100 × 70 mm coordinate system.

These are **not** centroid/CPL files and do not enumerate every passive. Final production coordinates must be exported from the routed PCB after connector mating-face orientation and rotations are verified.

The top high-current band distributes regulated 12 V from J1 to four AntHat-style fan connectors. The 12–15 V J6 logic input is a separate low-current domain; the optional JP1/diode feed may link the fan rail into the logic OR only when J1 is truly 12 V. USB can power logic independently.

The common 2×9 hashboard connector uses positions 1–16 and leaves 17/18 NC. Its UART/PLUG translator, I²C switch, gated 3.3 V source, and independent RESET buffer are fitted. The series RESET link is DNP/open in the default S21-safe assembly; fit it only for an exact legacy-reset profile that has passed bench validation.

There is no PSU-control interface in this revision. Consequently the PCB cannot guarantee hard removal of hashboard core power. Fault handling must stop work, use a verified hashboard-local shutdown command if available, disable cable I/O as the profile permits, and release fan PWM for full speed; failed local shutdown requires external power removal.

The module antenna shown at the lower edge assumes that edge is outside a metal enclosure. If the controller is fully inside an Antminer chassis, change U1 to a validated ESP32-S3 external-antenna module and recheck RF compliance and the BOM.
