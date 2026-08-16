#!/usr/bin/env python3
"""Perform dependency-free structural checks on ChainAxe design sources.

This validator intentionally does not replace KiCad ERC or DRC. It catches
repository errors early, including malformed CSV records, malformed component
designators, missing KiCad project files, duplicate references, and truncated
KiCad S-expressions.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


PROJECT_RELATIVE_DIR = Path("hardware/chainaxe")
PROJECT_BASENAME = "chainaxe"
ENGINEERING_BOM = Path("bom/chainaxe-reva-bom.csv")
REFERENCE_HEADERS = {
    "designator",
    "designators",
    "reference",
    "references",
    "ref",
    "refs",
    "reference/block",
}
REFERENCE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*[0-9]+(?:[A-Za-z]+)?$")
RANGE_RE = re.compile(
    r"^(?P<prefix>[A-Za-z][A-Za-z0-9]*?)(?P<start>[0-9]+)-"
    r"(?:(?P<prefix2>[A-Za-z][A-Za-z0-9]*?))?(?P<end>[0-9]+)$"
)
PROPERTY_REFERENCE_RE = re.compile(
    r'\(property\s+"Reference"\s+"([^"\\]*(?:\\.[^"\\]*)*)"'
)
PROPERTY_FOOTPRINT_RE = re.compile(
    r'\(property\s+"Footprint"\s+"([^"\\]*(?:\\.[^"\\]*)*)"'
)
PCB_FP_TEXT_REFERENCE_RE = re.compile(
    r'\(fp_text\s+reference\s+(?:"([^"\\]*(?:\\.[^"\\]*)*)"|([^\s()]+))'
)
PCB_ONLY_REFERENCE_RE = re.compile(r"^(?:H|FID)[0-9]+$")
CONNECTOR_PINOUT = Path("docs/connector-pinout.md")
CONNECTOR_INVARIANTS: dict[str, dict[str, str]] = {
    "J10": {
        "1": "GND",
        "2": "GND",
        "3": "HB_SDA",
        "4": "HB_SCL",
        "5": "HB_PLUG",
        "6": "HB_A2",
        "7": "HB_A1",
        "8": "HB_A0",
        "9": "GND",
        "10": "GND",
        "11": "HB_TX",
        "12": "HB_RX",
        "13": "GND",
        "14": "GND",
        "15": "HB_RESET",
        "16": "HB_3V3",
        "17": "NC",
        "18": "NC",
    },
    "J2-J5": {
        "1": "GND",
        "2": "FAN_12V",
        "3": "TACHn",
        "4": "PWMn",
    },
    "J1": {
        "1,2,3": "GND",
        "4,5,6": "FAN_12V_RAW",
    },
    "J6": {
        "1": "VIN_LOGIC_12_15",
        "2": "GND",
    },
}


@dataclass
class Results:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: Counter[str] = field(default_factory=Counter)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def split_reference_field(value: str) -> list[str]:
    """Return reference-like tokens from a CSV field.

    Commas, semicolons, and whitespace delimit references. For placement files,
    text after a valid first reference (for example, ``J2 FAN1``) is ignored
    only when the field contains no comma or semicolon.
    """

    value = value.strip()
    if not value or value.upper() in {"DNP", "TBD", "N/A", "NA", "NONE", "—", "-"}:
        return []

    if "," not in value and ";" not in value:
        words = value.split()
        if words and (REFERENCE_RE.fullmatch(words[0]) or RANGE_RE.fullmatch(words[0])):
            return [words[0]]

    return [part for part in re.split(r"[\s,;]+", value) if part]


def split_reference_block(value: str) -> list[str]:
    """Read the leading reference expression from a placement block label."""

    match = re.match(
        r"^\s*([A-Za-z][A-Za-z0-9]*[0-9]+(?:-[A-Za-z0-9]*[0-9]+)?)"
        r"((?:\s*[/,+]\s*[A-Za-z][A-Za-z0-9]*[0-9]+)*)",
        value,
    )
    if not match:
        return []
    references = [match.group(1)]
    references.extend(re.findall(r"[A-Za-z][A-Za-z0-9]*[0-9]+", match.group(2)))
    return references


def expand_reference(token: str) -> list[str]:
    token = token.strip()
    if REFERENCE_RE.fullmatch(token):
        return [token.upper()]

    match = RANGE_RE.fullmatch(token)
    if not match:
        raise ValueError(f"invalid designator {token!r}")

    prefix = match.group("prefix").upper()
    prefix2 = (match.group("prefix2") or prefix).upper()
    start = int(match.group("start"))
    end = int(match.group("end"))
    if prefix != prefix2:
        raise ValueError(f"range changes prefix in {token!r}")
    if end < start:
        raise ValueError(f"descending range {token!r}")
    if end - start > 999:
        raise ValueError(f"implausibly large range {token!r}")
    return [f"{prefix}{number}" for number in range(start, end + 1)]


def find_reference_column(header: list[str]) -> int | None:
    normalized = [name.strip().lower() for name in header]
    for index, name in enumerate(normalized):
        if name in REFERENCE_HEADERS:
            return index
    return None


def find_quantity_column(header: list[str]) -> int | None:
    normalized = [name.strip().lower() for name in header]
    for candidate in ("qty", "quantity"):
        if candidate in normalized:
            return normalized.index(candidate)
    return None


def validate_csv(path: Path, root: Path, results: Results) -> set[str]:
    location = relative(path, root)
    references: set[str] = set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        results.error(f"{location}: cannot read CSV: {exc}")
        return references

    results.checked["CSV files"] += 1
    if not rows:
        results.error(f"{location}: CSV is empty")
        return references

    header = rows[0]
    if not header or all(not cell.strip() for cell in header):
        results.error(f"{location}: header is empty")
        return references
    if any(not cell.strip() for cell in header):
        results.error(f"{location}: header contains an empty column name")
    duplicate_headers = [
        name for name, count in Counter(cell.strip().lower() for cell in header).items() if count > 1
    ]
    if duplicate_headers:
        results.error(f"{location}: duplicate columns: {', '.join(duplicate_headers)}")

    expected_width = len(header)
    reference_column = find_reference_column(header)
    quantity_column = find_quantity_column(header)
    seen: dict[str, int] = {}
    pseudo_references: list[str] = []

    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != expected_width:
            results.error(
                f"{location}:{line_number}: has {len(row)} fields; expected {expected_width}"
            )
            continue
        if not any(cell.strip() for cell in row):
            results.warn(f"{location}:{line_number}: blank record")
            continue
        if reference_column is None:
            continue

        field = row[reference_column].strip()
        expanded: list[str] = []
        reference_header = header[reference_column].strip().lower()
        tokens = (
            split_reference_block(field)
            if reference_header == "reference/block"
            else split_reference_field(field)
        )
        has_pseudo_reference = False
        for token in tokens:
            try:
                expanded.extend(expand_reference(token))
            except ValueError as exc:
                has_pseudo_reference = True
                pseudo_references.append(f"line {line_number} {token!r}")

        for reference in expanded:
            if reference in seen:
                results.error(
                    f"{location}:{line_number}: duplicate designator {reference}; "
                    f"first used on line {seen[reference]}"
                )
            else:
                seen[reference] = line_number
                references.add(reference)

        if quantity_column is not None and expanded and not has_pseudo_reference:
            quantity_text = row[quantity_column].strip()
            try:
                quantity = int(quantity_text)
            except ValueError:
                results.error(
                    f"{location}:{line_number}: quantity {quantity_text!r} is not an integer"
                )
            else:
                if quantity != len(expanded):
                    results.error(
                        f"{location}:{line_number}: quantity is {quantity}, but designators "
                        f"expand to {len(expanded)}"
                    )

    if reference_column is not None:
        results.checked["CSV designators"] += len(references)
    if pseudo_references:
        preview_count = 10
        preview = ", ".join(pseudo_references[:preview_count])
        remainder = max(0, len(pseudo_references) - preview_count)
        suffix = f", plus {remainder} more" if remainder else ""
        results.warn(
            f"{location}: {len(pseudo_references)} grouped or functional pseudo-designator(s) "
            f"not checked as concrete KiCad references: {preview}{suffix}"
        )
    return references


def normalize_markdown_cell(value: str) -> str:
    value = re.sub(r"[`*]", "", value)
    return re.sub(r"\s+", "", value.strip())


def markdown_section(text: str, heading_prefix: str) -> str:
    heading = re.search(
        rf"^##\s+{re.escape(heading_prefix)}(?:\s|—|$).*?$",
        text,
        flags=re.MULTILINE,
    )
    if not heading:
        return ""
    next_heading = re.search(r"^##\s+", text[heading.end() :], flags=re.MULTILINE)
    end = heading.end() + next_heading.start() if next_heading else len(text)
    return text[heading.end() : end]


def parse_pin_table(section: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        pin = normalize_markdown_cell(cells[0])
        net = normalize_markdown_cell(cells[1])
        if not re.fullmatch(r"[0-9]+(?:,[0-9]+)*", pin):
            continue
        mapping[pin] = net
    return mapping


def validate_connector_pinout(root: Path, results: Results) -> None:
    path = root / CONNECTOR_PINOUT
    location = relative(path, root)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        results.error(f"{location}: required connector pin map cannot be read: {exc}")
        return

    heading_prefixes = {
        "J10": "J10",
        "J2-J5": "J2–J5",
        "J1": "J1",
        "J6": "J6",
    }
    for connector, expected in CONNECTOR_INVARIANTS.items():
        section = markdown_section(text, heading_prefixes[connector])
        if not section:
            results.error(f"{location}: missing {connector} connector section")
            continue
        actual = parse_pin_table(section)
        if actual != expected:
            missing = [
                f"{pin}={net}" for pin, net in expected.items() if actual.get(pin) != net
            ]
            extra = [f"{pin}={net}" for pin, net in actual.items() if pin not in expected]
            detail = "; ".join(
                part
                for part in (
                    "missing or changed: " + ", ".join(missing) if missing else "",
                    "unexpected: " + ", ".join(extra) if extra else "",
                )
                if part
            )
            results.error(f"{location}: {connector} pin-map invariant failed ({detail})")
        else:
            results.checked["Connector pins"] += len(expected)

    j10 = parse_pin_table(markdown_section(text, "J10"))
    if j10.get("17") != "NC" or j10.get("18") != "NC":
        results.error(f"{location}: J10 pins 17 and 18 must both remain NC")


def sexpression_balance(text: str) -> tuple[bool, str]:
    """Check parentheses while ignoring quoted strings and semicolon comments."""

    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    line = 1

    for character in text:
        if character == "\n":
            line += 1
            in_comment = False
            continue
        if in_comment:
            continue
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == ";":
            in_comment = True
        elif character == '"':
            in_string = True
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False, f"unexpected ')' near line {line}"

    if in_string:
        return False, "unterminated quoted string"
    if depth:
        return False, f"unclosed parentheses (final depth {depth})"
    return True, ""


def sexpression_forms(text: str, requested_head: str) -> list[str]:
    """Return balanced forms with the requested first atom."""

    forms: list[str] = []
    stack: list[tuple[int, str]] = []
    in_string = False
    escaped = False
    in_comment = False
    index = 0
    length = len(text)

    while index < length:
        character = text[index]
        if character == "\n":
            in_comment = False
            index += 1
            continue
        if in_comment:
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == ";":
            in_comment = True
        elif character == '"':
            in_string = True
        elif character == "(":
            atom_match = re.match(r"\(([A-Za-z0-9_+-]+)", text[index:])
            stack.append((index, atom_match.group(1) if atom_match else ""))
        elif character == ")" and stack:
            start, head = stack.pop()
            if head == requested_head:
                forms.append(text[start : index + 1])
        index += 1
    return forms


def schematic_references(text: str) -> list[tuple[str, int]]:
    references: list[tuple[str, int]] = []
    for block in sexpression_forms(text, "symbol"):
        if not re.match(r"^\(symbol\s+\(lib_id(?:\s|\))", block):
            continue
        reference_match = PROPERTY_REFERENCE_RE.search(block)
        if not reference_match:
            continue
        unit_match = re.search(r"\(unit\s+([0-9]+)\)", block)
        references.append(
            (unescape_kicad(reference_match.group(1)).upper(), int(unit_match.group(1)) if unit_match else 1)
        )
    return references


def schematic_footprints(text: str) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for block in sexpression_forms(text, "symbol"):
        if not re.match(r"^\(symbol\s+\(lib_id(?:\s|\))", block):
            continue
        reference_match = PROPERTY_REFERENCE_RE.search(block)
        footprint_match = PROPERTY_FOOTPRINT_RE.search(block)
        if not reference_match or not footprint_match:
            continue
        reference = unescape_kicad(reference_match.group(1)).upper()
        footprint = unescape_kicad(footprint_match.group(1))
        if footprint:
            assignments[reference] = footprint
    return assignments


def form_position(form: str) -> tuple[str, str] | None:
    """Return a normalized KiCad ``(at x y ...)`` coordinate from a form."""

    match = re.search(r"\(at\s+(-?[0-9]+(?:\.[0-9]+)?)\s+(-?[0-9]+(?:\.[0-9]+)?)", form)
    if not match:
        return None

    def normalize(value: str) -> str:
        number = float(value)
        return f"{number:.6f}".rstrip("0").rstrip(".") or "0"

    return normalize(match.group(1)), normalize(match.group(2))


def validate_schematic_coordinate_conflicts(
    text: str, location: str, results: Results
) -> None:
    """Reject direct label/no-connect conflicts that would make ERC ambiguous."""

    labels_by_position: dict[tuple[str, str], set[str]] = {}
    for form in sexpression_forms(text, "label"):
        position = form_position(form)
        name_match = re.match(r'^\(label\s+"([^"\\]*(?:\\.[^"\\]*)*)"', form)
        if position is None or name_match is None:
            continue
        labels_by_position.setdefault(position, set()).add(
            unescape_kicad(name_match.group(1))
        )

    no_connect_positions = {
        position
        for form in sexpression_forms(text, "no_connect")
        if (position := form_position(form)) is not None
    }
    conflicts = sorted(set(labels_by_position) & no_connect_positions)
    if conflicts:
        preview = ", ".join(
            f"{position}={sorted(labels_by_position[position])}"
            for position in conflicts[:10]
        )
        suffix = f", plus {len(conflicts) - 10} more" if len(conflicts) > 10 else ""
        results.error(
            f"{location}: {len(conflicts)} coordinate(s) contain both a net label and "
            f"a no-connect marker: {preview}{suffix}"
        )

    multi_label = sorted(
        (position, names)
        for position, names in labels_by_position.items()
        if len(names) > 1
    )
    if multi_label:
        preview = ", ".join(
            f"{position}={sorted(names)}" for position, names in multi_label[:10]
        )
        suffix = f", plus {len(multi_label) - 10} more" if len(multi_label) > 10 else ""
        results.error(
            f"{location}: {len(multi_label)} coordinate(s) contain conflicting net labels: "
            f"{preview}{suffix}"
        )

    results.checked["Schematic net labels"] += sum(
        len(names) for names in labels_by_position.values()
    )


def pcb_references(text: str) -> tuple[list[str], list[str]]:
    references: list[str] = []
    pseudo_references: list[str] = []
    for block in sexpression_forms(text, "footprint"):
        property_match = PROPERTY_REFERENCE_RE.search(block)
        if property_match:
            reference = unescape_kicad(property_match.group(1)).upper()
        else:
            legacy_match = PCB_FP_TEXT_REFERENCE_RE.search(block)
            if not legacy_match:
                continue
            reference = unescape_kicad(
                legacy_match.group(1) or legacy_match.group(2)
            ).upper()

        library_match = re.match(r'^\(footprint\s+"([^"]+)"', block)
        is_test_point = bool(library_match and "TESTPOINT" in library_match.group(1).upper())
        if not REFERENCE_RE.fullmatch(reference) or (
            is_test_point and not re.fullmatch(r"TP[0-9]+", reference)
        ):
            pseudo_references.append(reference)
        else:
            references.append(reference)
    return references, pseudo_references


def footprint_reference(block: str) -> str | None:
    property_match = PROPERTY_REFERENCE_RE.search(block)
    if property_match:
        return unescape_kicad(property_match.group(1)).upper()
    legacy_match = PCB_FP_TEXT_REFERENCE_RE.search(block)
    if legacy_match:
        return unescape_kicad(legacy_match.group(1) or legacy_match.group(2)).upper()
    return None


def pcb_footprints(text: str) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for block in sexpression_forms(text, "footprint"):
        reference = footprint_reference(block)
        library_match = re.match(r'^\(footprint\s+"([^"\\]*(?:\\.[^"\\]*)*)"', block)
        if reference is None or library_match is None:
            continue
        assignments[reference] = unescape_kicad(library_match.group(1))
    return assignments


def engineering_bom_footprints(root: Path, results: Results) -> dict[str, str]:
    path = root / ENGINEERING_BOM
    assignments: dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        results.error(f"{relative(path, root)}: cannot read engineering BOM: {exc}")
        return assignments

    required = {"Designator", "Footprint"}
    if not rows or not required.issubset(rows[0]):
        results.error(
            f"{relative(path, root)}: missing required columns: "
            + ", ".join(sorted(required))
        )
        return assignments

    for line_number, row in enumerate(rows, start=2):
        footprint = row["Footprint"].strip()
        for token in split_reference_field(row["Designator"]):
            try:
                references = expand_reference(token)
            except ValueError:
                continue
            for reference in references:
                previous = assignments.get(reference)
                if previous is not None and previous != footprint:
                    results.error(
                        f"{relative(path, root)}:{line_number}: {reference} has conflicting "
                        f"footprints {previous!r} and {footprint!r}"
                    )
                assignments[reference] = footprint
    return assignments


def footprint_pad_map(block: str) -> tuple[dict[str, str | None], list[str]]:
    mapping: dict[str, str | None] = {}
    duplicates: list[str] = []
    for pad in sexpression_forms(block, "pad"):
        pad_match = re.match(r'^\(pad\s+(?:"([^"]*)"|([^\s()]+))', pad)
        if not pad_match:
            continue
        number = pad_match.group(1) if pad_match.group(1) is not None else pad_match.group(2)
        net_match = re.search(r'\(net\s+[0-9]+\s+"([^"\\]*(?:\\.[^"\\]*)*)"\)', pad)
        net = unescape_kicad(net_match.group(1)) if net_match else None
        if number == "" and net is None:
            # Manufacturer footprints commonly use blank-number NPTH locator
            # holes. They are mechanical features, not electrical contacts.
            continue
        if number in mapping and mapping[number] != net:
            duplicates.append(number)
        mapping[number] = net
    return mapping, duplicates


def validate_pcb_connector_maps(text: str, location: str, results: Results) -> None:
    footprints = {
        reference: block
        for block in sexpression_forms(text, "footprint")
        if (reference := footprint_reference(block)) is not None
    }
    expected_maps: dict[str, dict[str, str | None]] = {
        "J1": {
            "1": "GND",
            "2": "GND",
            "3": "GND",
            "4": "FAN_12V_RAW",
            "5": "FAN_12V_RAW",
            "6": "FAN_12V_RAW",
        },
        "J2": {"1": "GND", "2": "FAN_12V", "3": "FAN_TACH1", "4": "FAN_PWM1"},
        "J3": {"1": "GND", "2": "FAN_12V", "3": "FAN_TACH2", "4": "FAN_PWM2"},
        "J4": {"1": "GND", "2": "FAN_12V", "3": "FAN_TACH3", "4": "FAN_PWM3"},
        "J5": {"1": "GND", "2": "FAN_12V", "3": "FAN_TACH4", "4": "FAN_PWM4"},
        "J6": {"1": "VIN_LOGIC_12_15", "2": "GND"},
        "J30": {
            "A1": "GND",
            "A4": "USB_VBUS",
            "A5": "USB_CC1",
            "A6": "USB_DP_CONN",
            "A7": "USB_DN_CONN",
            "A8": None,
            "A9": "USB_VBUS",
            "A12": "GND",
            "B1": "GND",
            "B4": "USB_VBUS",
            "B5": "USB_CC2",
            "B6": "USB_DP_CONN",
            "B7": "USB_DN_CONN",
            "B8": None,
            "B9": "USB_VBUS",
            "B12": "GND",
            "S1": "USB_SHIELD",
        },
        "J10": {
            **CONNECTOR_INVARIANTS["J10"],
            "17": None,
            "18": None,
        },
    }
    for reference, expected in expected_maps.items():
        block = footprints.get(reference)
        if block is None:
            results.error(f"{location}: required connector footprint {reference} is missing")
            continue
        actual, duplicates = footprint_pad_map(block)
        if duplicates:
            results.error(
                f"{location}: {reference} has conflicting duplicate pad(s): "
                + ", ".join(sorted(set(duplicates)))
            )
        mismatches = [
            f"{pin}={actual.get(pin)!r} (expected {net!r})"
            for pin, net in expected.items()
            if actual.get(pin) != net
        ]
        unexpected = sorted(set(actual) - set(expected))
        if mismatches or unexpected:
            details = mismatches + (["unexpected pads " + ", ".join(unexpected)] if unexpected else [])
            results.error(f"{location}: {reference} pin-map invariant failed: " + "; ".join(details))
        else:
            results.checked["PCB connector pads"] += len(expected)


def validate_kicad_sexpression(
    path: Path, root: Path, expected_root: str, results: Results
) -> str:
    location = relative(path, root)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        results.error(f"{location}: cannot read KiCad source: {exc}")
        return ""

    results.checked["KiCad S-expression files"] += 1
    if not re.match(rf"^\s*\({re.escape(expected_root)}(?:\s|\))", text):
        results.error(f"{location}: expected root expression ({expected_root} ...)")
    balanced, detail = sexpression_balance(text)
    if not balanced:
        results.error(f"{location}: malformed S-expression: {detail}")
    return text


def unescape_kicad(value: str) -> str:
    return value.replace(r'\"', '"').replace(r"\\", "\\")


def duplicate_references(references: Iterable[str]) -> list[str]:
    return sorted(reference for reference, count in Counter(references).items() if count > 1)


def validate_kicad_project(root: Path, results: Results) -> None:
    project_dir = root / PROJECT_RELATIVE_DIR
    project_file = project_dir / f"{PROJECT_BASENAME}.kicad_pro"
    schematic_file = project_dir / f"{PROJECT_BASENAME}.kicad_sch"
    pcb_file = project_dir / f"{PROJECT_BASENAME}.kicad_pcb"

    for path in (project_file, schematic_file, pcb_file):
        if not path.is_file():
            results.error(f"{relative(path, root)}: required KiCad project file is missing")

    if project_file.is_file():
        try:
            with project_file.open("r", encoding="utf-8") as handle:
                project_data = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            results.error(f"{relative(project_file, root)}: invalid KiCad project JSON: {exc}")
        else:
            if not isinstance(project_data, dict):
                results.error(f"{relative(project_file, root)}: project JSON root must be an object")
            results.checked["KiCad project files"] += 1

    schematic_text = ""
    pcb_text = ""
    if schematic_file.is_file():
        schematic_text = validate_kicad_sexpression(
            schematic_file, root, "kicad_sch", results
        )
        validate_schematic_coordinate_conflicts(
            schematic_text, relative(schematic_file, root), results
        )
    if pcb_file.is_file():
        pcb_text = validate_kicad_sexpression(pcb_file, root, "kicad_pcb", results)

    schematic_ref_units = [
        (reference, unit)
        for reference, unit in schematic_references(schematic_text)
        if not reference.startswith("#")
    ]
    schematic_refs = [reference for reference, _unit in schematic_ref_units]
    all_pcb_refs, pcb_pseudo_refs = pcb_references(pcb_text)
    pcb_refs = [reference for reference in all_pcb_refs if not reference.startswith("#")]
    schematic_fp = schematic_footprints(schematic_text)
    pcb_fp = pcb_footprints(pcb_text)
    bom_fp = engineering_bom_footprints(root, results)
    if pcb_pseudo_refs:
        preview_count = 10
        preview = ", ".join(pcb_pseudo_refs[:preview_count])
        remainder = len(pcb_pseudo_refs) - preview_count
        suffix = f", plus {remainder} more" if remainder else ""
        results.warn(
            f"{relative(pcb_file, root)}: {len(pcb_pseudo_refs)} functional footprint "
            f"reference(s) treated as pseudo-designators: {preview}{suffix}"
        )

    for source_name, references in ((relative(pcb_file, root), pcb_refs),):
        for reference in references:
            if not REFERENCE_RE.fullmatch(reference):
                results.error(f"{source_name}: invalid component reference {reference!r}")
        duplicates = duplicate_references(references)
        if duplicates:
            results.error(f"{source_name}: duplicate references: {', '.join(duplicates)}")

    schematic_units_by_reference: dict[str, list[int]] = {}
    for reference, unit in schematic_ref_units:
        if not REFERENCE_RE.fullmatch(reference):
            results.error(
                f"{relative(schematic_file, root)}: invalid component reference {reference!r}"
            )
        schematic_units_by_reference.setdefault(reference, []).append(unit)
    schematic_duplicates = sorted(
        reference
        for reference, units in schematic_units_by_reference.items()
        if len(units) != len(set(units))
    )
    if schematic_duplicates:
        results.error(
            f"{relative(schematic_file, root)}: duplicate references with the same unit: "
            + ", ".join(schematic_duplicates)
        )

    if schematic_refs:
        results.checked["Schematic references"] += len(set(schematic_refs))
    if pcb_refs:
        results.checked["PCB references"] += len(set(pcb_refs))
        validate_pcb_connector_maps(pcb_text, relative(pcb_file, root), results)
    if schematic_refs and pcb_refs:
        missing_from_schematic = sorted(
            reference
            for reference in set(pcb_refs) - set(schematic_refs)
            if not PCB_ONLY_REFERENCE_RE.fullmatch(reference)
        )
        if missing_from_schematic:
            results.error(
                "PCB references not found in schematic: " + ", ".join(missing_from_schematic)
            )
        missing_from_pcb = sorted(set(schematic_refs) - set(pcb_refs))
        if missing_from_pcb:
            results.warn(
                "Schematic references not yet placed on PCB: " + ", ".join(missing_from_pcb)
            )
        footprint_mismatches = sorted(
            (reference, schematic_fp[reference], pcb_fp[reference])
            for reference in set(schematic_fp) & set(pcb_fp)
            if schematic_fp[reference] != pcb_fp[reference]
        )
        if footprint_mismatches:
            preview = ", ".join(
                f"{reference}: schematic={schematic!r}, PCB={pcb!r}"
                for reference, schematic, pcb in footprint_mismatches[:10]
            )
            suffix = (
                f", plus {len(footprint_mismatches) - 10} more"
                if len(footprint_mismatches) > 10
                else ""
            )
            results.error(
                "Schematic/PCB footprint assignment mismatches: " + preview + suffix
            )
        else:
            results.checked["Matched schematic/PCB footprints"] += len(
                set(schematic_fp) & set(pcb_fp)
            )

        bom_missing = sorted(set(schematic_fp) - set(bom_fp))
        if bom_missing:
            results.error(
                "Schematic references missing from engineering BOM: " + ", ".join(bom_missing)
            )
        bom_footprint_mismatches = sorted(
            (reference, schematic_fp[reference], bom_fp[reference])
            for reference in set(schematic_fp) & set(bom_fp)
            if schematic_fp[reference] != bom_fp[reference]
        )
        if bom_footprint_mismatches:
            preview = ", ".join(
                f"{reference}: schematic={schematic!r}, BOM={bom!r}"
                for reference, schematic, bom in bom_footprint_mismatches[:10]
            )
            suffix = (
                f", plus {len(bom_footprint_mismatches) - 10} more"
                if len(bom_footprint_mismatches) > 10
                else ""
            )
            results.error("Schematic/BOM footprint assignment mismatches: " + preview + suffix)
        else:
            results.checked["Matched schematic/BOM footprints"] += len(
                set(schematic_fp) & set(bom_fp)
            )

        custom_footprints = sorted(
            footprint.split(":", 1)[1]
            for footprint in set(schematic_fp.values())
            if footprint.startswith("ChainAxe:")
        )
        local_library = project_dir / "ChainAxe.pretty"
        fp_table = project_dir / "fp-lib-table"
        if custom_footprints and not fp_table.is_file():
            results.error(f"{relative(fp_table, root)}: required project footprint table is missing")
        for name in custom_footprints:
            footprint_file = local_library / f"{name}.kicad_mod"
            if not footprint_file.is_file():
                results.error(
                    f"{relative(footprint_file, root)}: custom schematic footprint is missing"
                )
        results.checked["Project-local footprint files"] += sum(
            (local_library / f"{name}.kicad_mod").is_file()
            for name in custom_footprints
        )


def validate_repository(root: Path) -> Results:
    results = Results()
    csv_files = sorted(
        path for path in root.rglob("*.csv") if ".git" not in path.parts
    )
    if not csv_files:
        results.error("no CSV design sources found")
    for csv_file in csv_files:
        validate_csv(csv_file, root, results)

    validate_connector_pinout(root, results)
    validate_kicad_project(root, results)
    return results


def print_results(results: Results) -> None:
    for message in results.errors:
        print(f"ERROR: {message}")
    for message in results.warnings:
        print(f"WARNING: {message}")

    summary = ", ".join(
        f"{count} {label.lower()}" for label, count in sorted(results.checked.items())
    )
    if summary:
        print(f"Checked {summary}.")
    print(
        f"Validation completed with {len(results.errors)} error(s) and "
        f"{len(results.warnings)} warning(s)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        type=Path,
        help="repository root (default: current directory)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"repository root is not a directory: {root}")

    results = validate_repository(root)
    print_results(results)
    return 1 if results.errors else 0


if __name__ == "__main__":
    sys.exit(main())
