#!/usr/bin/env python3
"""Validate every ChainAxe schematic pin against the audited net/NC contract.

KiCad symbol-library coordinates use Y-up while schematic coordinates use
Y-down. This validator deliberately performs that transform itself instead of
using a third-party endpoint helper. It currently rejects rotated or mirrored
instances so a future layout change cannot silently bypass the audited model.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


TOKEN_RE = re.compile(r'\s*(?:(\()|(\))|("(?:\\.|[^"\\])*")|([^\s()]+))')


def parse_sexpression(text: str) -> list:
    """Parse the KiCad S-expression using only the Python standard library."""

    outer: list = []
    stack = [outer]
    position = 0
    while position < len(text):
        match = TOKEN_RE.match(text, position)
        if match is None:
            if text[position:].strip():
                raise ValueError(f"unexpected token at byte {position}")
            break
        position = match.end()
        left, right, quoted, atom = match.groups()
        if left:
            node: list = []
            stack[-1].append(node)
            stack.append(node)
        elif right:
            if len(stack) == 1:
                raise ValueError("unmatched closing parenthesis")
            stack.pop()
        elif quoted is not None:
            stack[-1].append(json.loads(quoted))
        elif atom is not None:
            stack[-1].append(atom)
    if len(stack) != 1:
        raise ValueError("unclosed parenthesis")
    if len(outer) != 1 or not isinstance(outer[0], list):
        raise ValueError("expected one root S-expression")
    return outer[0]


def tag(node: object) -> str:
    return str(node[0]) if isinstance(node, list) and node else ""


def child(node: list, name: str) -> list | None:
    for item in node[1:]:
        if tag(item) == name:
            return item
    return None


def descendants(node: object, name: str):
    if not isinstance(node, list):
        return
    if tag(node) == name:
        yield node
    for item in node:
        if isinstance(item, list):
            yield from descendants(item, name)


def coordinate(x: object, y: object) -> tuple[float, float]:
    return (round(float(str(x)), 6), round(float(str(y)), 6))


def reference_of(symbol: list) -> str:
    for item in symbol:
        if tag(item) == "property" and str(item[1]) == "Reference":
            return str(item[2])
    raise ValueError("placed symbol lacks Reference property")


def read_audit(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "Component", "LibID", "Pin", "PinFunction", "ExpectedConnection",
            "ActualConnection", "Status",
        }
        if set(reader.fieldnames or []) != required:
            raise ValueError(f"{path}: columns must be exactly {sorted(required)}")
        rows: dict[tuple[str, str], dict[str, str]] = {}
        for line_number, row in enumerate(reader, start=2):
            key = (row["Component"], row["Pin"])
            if key in rows:
                raise ValueError(f"{path}:{line_number}: duplicate {key[0]}.{key[1]}")
            rows[key] = row
    return rows


def validate(schematic_path: Path, audit_path: Path) -> list[str]:
    errors: list[str] = []
    root = parse_sexpression(schematic_path.read_text(encoding="utf-8"))
    audit = read_audit(audit_path)

    lib_container = child(root, "lib_symbols")
    if lib_container is None:
        return ["schematic has no embedded lib_symbols"]
    libraries = {
        str(symbol[1]): symbol
        for symbol in lib_container[1:]
        if tag(symbol) == "symbol"
    }

    pin_defs: dict[str, dict[str, tuple[str, float, float]]] = {}
    for lib_id, symbol in libraries.items():
        pins: dict[str, tuple[str, float, float]] = {}
        for pin in descendants(symbol, "pin"):
            at = child(pin, "at")
            number = child(pin, "number")
            name = child(pin, "name")
            if at is None or number is None or name is None:
                continue
            entry = (str(name[1]), float(str(at[1])), float(str(at[2])))
            pin_number = str(number[1])
            if pin_number in pins and pins[pin_number] != entry:
                errors.append(
                    f"ambiguous embedded pin {lib_id}.{pin_number}: "
                    f"{pins[pin_number]} vs {entry}"
                )
            pins[pin_number] = entry
        pin_defs[lib_id] = pins

    labels: dict[tuple[float, float], str] = {}
    no_connects: set[tuple[float, float]] = set()
    placed: dict[str, tuple[str, float, float]] = {}
    for item in root[1:]:
        if tag(item) == "label":
            at = child(item, "at")
            position = coordinate(at[1], at[2])
            if position in labels:
                errors.append(f"multiple labels at {position}: {labels[position]} and {item[1]}")
            labels[position] = str(item[1])
        elif tag(item) == "no_connect":
            at = child(item, "at")
            no_connects.add(coordinate(at[1], at[2]))
        elif tag(item) == "symbol" and child(item, "lib_id") is not None:
            ref = reference_of(item)
            lib_id = str(child(item, "lib_id")[1])
            at = child(item, "at")
            mirror = child(item, "mirror")
            if float(str(at[3])) != 0 or mirror is not None:
                errors.append(
                    f"{ref}: rotated/mirrored instance is outside audited transform: "
                    f"at={at[1:]}, mirror={mirror}"
                )
            placed[ref] = (lib_id, float(str(at[1])), float(str(at[2])))

    overlap = set(labels) & no_connects
    if overlap:
        errors.append(f"label and NC share endpoint(s): {sorted(overlap)}")

    endpoints: dict[tuple[float, float], list[tuple[str, str]]] = defaultdict(list)
    calculated_keys: set[tuple[str, str]] = set()
    for ref, (lib_id, instance_x, instance_y) in placed.items():
        if lib_id not in pin_defs:
            errors.append(f"{ref}: embedded library {lib_id} not found")
            continue
        for pin_number, (pin_name, local_x, local_y) in pin_defs[lib_id].items():
            key = (ref, pin_number)
            calculated_keys.add(key)
            # KiCad library symbols are Y-up; schematic coordinates are Y-down.
            position = coordinate(instance_x + local_x, instance_y - local_y)
            endpoints[position].append(key)
            marker = labels.get(position)
            if position in no_connects:
                marker = "NC" if marker is None else f"{marker}+NC"
            if marker is None:
                marker = "UNMARKED"

            row = audit.get(key)
            if row is None:
                errors.append(f"audit missing {ref}.{pin_number} {pin_name} at {position}")
                continue
            if row["LibID"] != lib_id:
                errors.append(f"{ref}.{pin_number}: LibID {lib_id} != audit {row['LibID']}")
            if row["PinFunction"] != pin_name:
                errors.append(
                    f"{ref}.{pin_number}: function {pin_name} != audit {row['PinFunction']}"
                )
            if row["ExpectedConnection"] != marker:
                errors.append(
                    f"{ref}.{pin_number} {pin_name}: actual {marker} at {position}, "
                    f"expected {row['ExpectedConnection']}"
                )
            if row["ActualConnection"] != marker or row["Status"] != "PASS":
                errors.append(
                    f"{ref}.{pin_number}: stale audit result actual={row['ActualConnection']} "
                    f"status={row['Status']}; calculated actual={marker}"
                )

    extra_rows = set(audit) - calculated_keys
    if extra_rows:
        errors.append(f"audit contains pins absent from schematic: {sorted(extra_rows)}")

    pin_positions = set(endpoints)
    if set(labels) - pin_positions:
        errors.append(f"labels off all pin endpoints: {sorted(set(labels) - pin_positions)}")
    if no_connects - pin_positions:
        errors.append(f"NC markers off all pin endpoints: {sorted(no_connects - pin_positions)}")

    cross_component = {
        position: claims
        for position, claims in endpoints.items()
        if len({ref for ref, _ in claims}) > 1
    }
    if cross_component:
        errors.append(f"cross-component pin endpoint collisions: {cross_component}")

    if not errors:
        print(
            "Pin-map validation passed: "
            f"{len(placed)} components, {len(calculated_keys)} pins, "
            f"{len(labels)} labels, {len(no_connects)} NC markers, "
            "0 mismatches, 0 cross-component endpoint collisions."
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()
    schematic = args.root / "hardware/chainaxe/chainaxe.kicad_sch"
    audit = args.root / "hardware/chainaxe/pin-net-audit.csv"
    try:
        errors = validate(schematic, audit)
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
