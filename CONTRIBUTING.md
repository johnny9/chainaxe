# Contributing to ChainAxe

ChainAxe is an early-stage open-hardware controller. It has not yet been
validated on a production Antminer hashboard. Contributions are welcome, but
no design should be described as production-ready until it has passed the
release checks below.

## Before you start

Open an issue before making a change that affects the 18-position/16-used
hashboard interface, input protection, voltage rails, fan power path, mechanical outline,
or supported hashboard list. Describe the target hashboard by its exact model,
board revision, ASIC, and measured cable pinout. A family name such as "S19" or
"S21" is not enough to approve an electrical-interface change.

Do not include proprietary Bitmain files, firmware, schematics, or other
material that you do not have permission to redistribute. Cite public sources
and clearly separate measured facts from assumptions.

## Development workflow

1. Create a focused branch from `main`.
2. Make the smallest coherent change.
3. Update the schematic, PCB, BOM, interface documentation, and design notes
   together when the change affects more than one of them.
4. Run all three source validators:
   `python3 scripts/validate_design.py .`,
   `python3 scripts/validate_schematic_pinmap.py .`, and
   `python3 scripts/validate_pcb_geometry.py .`.
5. Run KiCad ERC and DRC when KiCad is available. The source validators do not
   replace either native check. Attach the reports or explain
   every remaining exclusion in the pull request.
6. Include screenshots or plots for layout, signal-integrity, power, or thermal
   changes when they make the review easier.

Keep generated fabrication files out of ordinary development pull requests.
Release fabrication outputs must identify the exact source revision from which
they were generated.

## Hardware change requirements

Hardware pull requests should include:

- the reason for the change and the affected revision;
- exact manufacturer part numbers and footprints for added components;
- current JLCPCB/LCSC availability status, where applicable;
- voltage, current, power, tolerance, and temperature checks;
- connector pin-one and mating-orientation evidence;
- safe startup and unpowered-state behavior;
- bench-test results, or an explicit `UNTESTED` label if no hardware exists;
- updates to the BOM and assembly-population fields.

Do not remove protection, interlocks, default-off enables, test points, or
measurement gates only to reduce cost without documenting the resulting risk.

## Style

- Use SI units and include a space between a value and its unit.
- Use active, direct language in documentation.
- Use one designator per physical component. Ranges such as `R1-R4` are allowed
  in BOM rows only when every component has the same value, footprint, and
  population status.
- Mark provisional selections and unverified pinouts plainly.

## Licensing

By contributing, you agree that your contribution is made available under the
repository's CERN Open Hardware Licence Version 2 - Strongly Reciprocal
(`CERN-OHL-S-2.0`). Retain existing notices and add modification notices where
the licence requires them.
