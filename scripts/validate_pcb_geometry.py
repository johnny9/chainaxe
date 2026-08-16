#!/usr/bin/env python3
"""Catch gross placement shorts and component collisions in a KiCad PCB.

This is deliberately a small, dependency-free source check, not a replacement
for KiCad DRC.  It understands the legacy ``kicad_pcb`` S-expression used by
this project and checks three classes of placement error that are otherwise
easy to miss in review:

* copper-bearing pads on different nets that physically intersect;
* NPTH/locator/mounting holes that intersect another component's copper pad;
* overlapping component bodies/courtyards, and unexpected board-edge overhang.

Same-net and same-footprint pad stacks are intentional in several thermal and
connector footprints, so they are ignored.  Paste-only apertures and board
vias are not component pads and are also ignored.  The final authority remains
KiCad ERC/DRC plus mechanical and first-article fit review.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Iterator, Sequence


EPSILON = 1.0e-7
ARC_STEPS = 8

# These connector bodies intentionally cross an Edge.Cuts boundary so that the
# mating face is accessible.  Their footprint drawings and first-article fit
# requirements are documented in hardware/chainaxe/README.md and
# docs/connector-pinout.md.  U1's antenna courtyard deliberately continues
# beyond the bottom board edge.
DOCUMENTED_EDGE_OVERHANGS = frozenset(
    {"J1", "J2", "J3", "J4", "J5", "J6", "J10", "J30", "U1"}
)


class ParseError(ValueError):
    """Raised when the PCB S-expression cannot be parsed safely."""


Point = tuple[float, float]
Polygon = list[Point]
SExpr = str | list["SExpr"]


@dataclass
class Pad:
    ref: str
    number: str
    kind: str
    shape: str
    net: str | None
    copper_layers: frozenset[str]
    polygon: Polygon
    center: Point
    mechanical_hole: bool = False

    @property
    def label(self) -> str:
        number = self.number if self.number else "<unnumbered>"
        return f"{self.ref}.{number}"


@dataclass
class Footprint:
    name: str
    ref: str
    layer: str
    at: Point
    angle: float
    pads: list[Pad] = field(default_factory=list)
    outlines: list[Polygon] = field(default_factory=list)
    outline_source: str = "none"

    @property
    def is_mounting_hole(self) -> bool:
        return self.ref.startswith("H") or (
            bool(self.pads) and all(p.mechanical_hole for p in self.pads)
        )


@dataclass(frozen=True)
class Finding:
    category: str
    message: str


def tokenize(text: str) -> Iterator[str]:
    """Tokenize a KiCad S-expression while preserving quoted atom contents."""

    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char in "()":
            yield char
            index += 1
            continue
        if char == '"':
            index += 1
            value: list[str] = []
            while index < length:
                char = text[index]
                if char == '"':
                    index += 1
                    break
                if char == "\\":
                    index += 1
                    if index >= length:
                        raise ParseError("unterminated escape in quoted string")
                    escaped = text[index]
                    value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    index += 1
                    continue
                value.append(char)
                index += 1
            else:
                raise ParseError("unterminated quoted string")
            yield "".join(value)
            continue
        start = index
        while index < length and not text[index].isspace() and text[index] not in "()":
            index += 1
        yield text[start:index]


def parse_sexpr(text: str) -> list[SExpr]:
    """Parse text into a minimal nested-list S-expression representation."""

    roots: list[SExpr] = []
    stack: list[list[SExpr]] = []
    for token in tokenize(text):
        if token == "(":
            node: list[SExpr] = []
            if stack:
                stack[-1].append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ParseError("unexpected closing parenthesis")
            stack.pop()
        elif not stack:
            raise ParseError(f"atom outside list: {token!r}")
        else:
            stack[-1].append(token)
    if stack:
        raise ParseError("unterminated list")
    return roots


def head(node: SExpr) -> str | None:
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return None


def child(node: Sequence[SExpr], name: str) -> list[SExpr] | None:
    return next(
        (
            item
            for item in node[1:]
            if isinstance(item, list) and item and item[0] == name
        ),
        None,
    )


def children(node: Sequence[SExpr], name: str) -> Iterator[list[SExpr]]:
    for item in node[1:]:
        if isinstance(item, list) and item and item[0] == name:
            yield item


def atom(node: Sequence[SExpr] | None, index: int, default: str | None = None) -> str | None:
    if node is None or len(node) <= index or not isinstance(node[index], str):
        return default
    return node[index]


def number(value: str | None, context: str) -> float:
    if value is None:
        raise ParseError(f"missing number for {context}")
    try:
        return float(value)
    except ValueError as exc:
        raise ParseError(f"invalid number for {context}: {value!r}") from exc


def xy(node: Sequence[SExpr] | None, context: str) -> Point:
    return (number(atom(node, 1), context), number(atom(node, 2), context))


def rotate(point: Point, degrees: float) -> Point:
    radians = math.radians(degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    x_value, y_value = point
    return (
        x_value * cosine - y_value * sine,
        x_value * sine + y_value * cosine,
    )


def translate(point: Point, offset: Point) -> Point:
    return (point[0] + offset[0], point[1] + offset[1])


def footprint_transform(point: Point, footprint: Footprint) -> Point:
    # KiCad mirrors a bottom-side footprint in its local X direction before
    # applying the footprint rotation.  ChainAxe Rev A.1 is currently all top
    # side, but handling the mirror costs little and avoids a silent bad read.
    local = (-point[0], point[1]) if footprint.layer.startswith("B.") else point
    return translate(rotate(local, footprint.angle), footprint.at)


def regular_circle(center: Point, radius: float, steps: int = 32) -> Polygon:
    return [
        (
            center[0] + radius * math.cos(2.0 * math.pi * index / steps),
            center[1] + radius * math.sin(2.0 * math.pi * index / steps),
        )
        for index in range(steps)
    ]


def rounded_rectangle(width: float, height: float, radius: float) -> Polygon:
    half_width = width / 2.0
    half_height = height / 2.0
    radius = max(0.0, min(radius, half_width, half_height))
    if radius <= EPSILON:
        return [
            (-half_width, -half_height),
            (half_width, -half_height),
            (half_width, half_height),
            (-half_width, half_height),
        ]
    points: Polygon = []
    for center_x, center_y, start_angle in (
        (half_width - radius, -half_height + radius, -90.0),
        (half_width - radius, half_height - radius, 0.0),
        (-half_width + radius, half_height - radius, 90.0),
        (-half_width + radius, -half_height + radius, 180.0),
    ):
        for step in range(ARC_STEPS + 1):
            angle = math.radians(start_angle + 90.0 * step / ARC_STEPS)
            points.append(
                (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
            )
    return points


def oval(width: float, height: float) -> Polygon:
    if abs(width - height) <= EPSILON:
        return regular_circle((0.0, 0.0), width / 2.0)
    points: Polygon = []
    if width > height:
        radius = height / 2.0
        half_segment = (width - height) / 2.0
        for center_x, start_angle in ((half_segment, -90.0), (-half_segment, 90.0)):
            for step in range(2 * ARC_STEPS + 1):
                angle = math.radians(start_angle + 180.0 * step / (2 * ARC_STEPS))
                points.append((center_x + radius * math.cos(angle), radius * math.sin(angle)))
    else:
        radius = width / 2.0
        half_segment = (height - width) / 2.0
        for center_y, start_angle in ((half_segment, 0.0), (-half_segment, 180.0)):
            for step in range(2 * ARC_STEPS + 1):
                angle = math.radians(start_angle + 180.0 * step / (2 * ARC_STEPS))
                points.append((radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return points


def pad_polygon(
    shape: str,
    width: float,
    height: float,
    roundrect_ratio: float,
) -> Polygon:
    if shape == "circle":
        return regular_circle((0.0, 0.0), min(width, height) / 2.0)
    if shape == "oval":
        return oval(width, height)
    if shape == "roundrect":
        return rounded_rectangle(width, height, min(width, height) * roundrect_ratio)
    if shape in {"rect", "trapezoid"}:
        # Trapezoids are not used by this board.  Treating one as its declared
        # bounding rectangle is conservative until primitive delta support is
        # needed.
        return rounded_rectangle(width, height, 0.0)
    raise ParseError(f"unsupported copper pad shape: {shape!r}")


def transform_pad_polygon(
    local_polygon: Polygon,
    local_center: Point,
    pad_angle: float,
    footprint: Footprint,
) -> Polygon:
    transformed: Polygon = []
    for point in local_polygon:
        local = translate(rotate(point, pad_angle), local_center)
        transformed.append(footprint_transform(local, footprint))
    return transformed


def copper_layers(pad_node: Sequence[SExpr]) -> frozenset[str]:
    layers = child(pad_node, "layers")
    values = {
        item
        for item in (layers[1:] if layers else [])
        if isinstance(item, str)
        and (item.endswith(".Cu") or item in {"*.Cu", "F&B.Cu"})
    }
    if "*.Cu" in values or "F&B.Cu" in values:
        return frozenset({"*"})
    return frozenset(values)


def parse_drill_polygon(pad_node: Sequence[SExpr], footprint: Footprint, local_at: Point, angle: float) -> Polygon:
    drill = child(pad_node, "drill")
    if drill is None:
        raise ParseError(f"NPTH in {footprint.ref} has no drill")
    values = [item for item in drill[1:] if isinstance(item, str)]
    if values and values[0] == "oval":
        if len(values) < 3:
            raise ParseError(f"invalid oval drill in {footprint.ref}")
        width = number(values[1], "drill width")
        height = number(values[2], "drill height")
        local_polygon = oval(width, height)
    else:
        if not values:
            raise ParseError(f"invalid drill in {footprint.ref}")
        width = number(values[0], "drill diameter")
        height = number(values[1], "drill height") if len(values) > 1 else width
        local_polygon = oval(width, height)
    return transform_pad_polygon(local_polygon, local_at, angle, footprint)


def parse_pad(pad_node: Sequence[SExpr], footprint: Footprint) -> Pad | None:
    pad_number = atom(pad_node, 1, "") or ""
    kind = atom(pad_node, 2, "") or ""
    shape = atom(pad_node, 3, "") or ""
    at_node = child(pad_node, "at")
    local_at = xy(at_node, f"{footprint.ref}.{pad_number} pad position")
    pad_angle = number(atom(at_node, 3, "0"), "pad angle")

    if kind == "np_thru_hole":
        polygon = parse_drill_polygon(pad_node, footprint, local_at, pad_angle)
        return Pad(
            ref=footprint.ref,
            number=pad_number,
            kind=kind,
            shape=shape,
            net=None,
            copper_layers=frozenset(),
            polygon=polygon,
            center=footprint_transform(local_at, footprint),
            mechanical_hole=True,
        )

    layers = copper_layers(pad_node)
    if not layers:
        # In particular, ignore the unnumbered F.Paste thermal apertures.
        return None
    size_node = child(pad_node, "size")
    width, height = xy(size_node, f"{footprint.ref}.{pad_number} pad size")
    ratio_node = child(pad_node, "roundrect_rratio")
    ratio = number(atom(ratio_node, 1, "0"), "roundrect ratio")
    local_polygon = pad_polygon(shape, width, height, ratio)
    polygon = transform_pad_polygon(local_polygon, local_at, pad_angle, footprint)
    net_node = child(pad_node, "net")
    net_name = atom(net_node, 2) if net_node is not None else None
    return Pad(
        ref=footprint.ref,
        number=pad_number,
        kind=kind,
        shape=shape,
        net=net_name,
        copper_layers=layers,
        polygon=polygon,
        center=footprint_transform(local_at, footprint),
    )


def graphic_layer(node: Sequence[SExpr]) -> str | None:
    return atom(child(node, "layer"), 1)


def rect_polygon(node: Sequence[SExpr]) -> Polygon:
    start = xy(child(node, "start"), "rectangle start")
    end = xy(child(node, "end"), "rectangle end")
    return [start, (end[0], start[1]), end, (start[0], end[1])]


def circle_polygon(node: Sequence[SExpr]) -> Polygon:
    center = xy(child(node, "center"), "circle center")
    edge = xy(child(node, "end"), "circle edge")
    radius = math.hypot(edge[0] - center[0], edge[1] - center[1])
    return regular_circle(center, radius)


def poly_polygon(node: Sequence[SExpr]) -> Polygon:
    points_node = child(node, "pts")
    if points_node is None:
        return []
    return [xy(item, "polygon point") for item in children(points_node, "xy")]


def point_key(point: Point) -> tuple[int, int]:
    return (round(point[0] * 1_000_000), round(point[1] * 1_000_000))


def closed_line_polygons(lines: Sequence[tuple[Point, Point]]) -> list[Polygon]:
    """Convert independent KiCad line segments into simple closed loops."""

    adjacency: dict[tuple[int, int], list[int]] = {}
    for index, (start, end) in enumerate(lines):
        adjacency.setdefault(point_key(start), []).append(index)
        adjacency.setdefault(point_key(end), []).append(index)
    unused = set(range(len(lines)))
    polygons: list[Polygon] = []
    while unused:
        first = min(unused)
        unused.remove(first)
        start, end = lines[first]
        polygon = [start, end]
        current_key = point_key(end)
        start_key = point_key(start)
        while current_key != start_key:
            candidates = [index for index in adjacency.get(current_key, []) if index in unused]
            if not candidates:
                break
            next_index = min(candidates)
            unused.remove(next_index)
            next_start, next_end = lines[next_index]
            if point_key(next_start) == current_key:
                next_point = next_end
            else:
                next_point = next_start
            polygon.append(next_point)
            current_key = point_key(next_point)
        if current_key == start_key and len(polygon) >= 4:
            polygon.pop()  # repeated closing point
            polygons.append(polygon)
    return polygons


def local_outline_polygons(footprint_node: Sequence[SExpr], layer: str) -> list[Polygon]:
    polygons: list[Polygon] = []
    lines: list[tuple[Point, Point]] = []
    for item in footprint_node[1:]:
        if not isinstance(item, list) or graphic_layer(item) != layer:
            continue
        item_head = head(item)
        if item_head == "fp_rect":
            polygons.append(rect_polygon(item))
        elif item_head == "fp_circle":
            polygons.append(circle_polygon(item))
        elif item_head == "fp_poly":
            polygon = poly_polygon(item)
            if len(polygon) >= 3:
                polygons.append(polygon)
        elif item_head == "fp_line":
            lines.append((xy(child(item, "start"), "line start"), xy(child(item, "end"), "line end")))
    polygons.extend(closed_line_polygons(lines))
    return polygons


def parse_footprint(node: Sequence[SExpr]) -> Footprint:
    name = atom(node, 1, "<unnamed>") or "<unnamed>"
    layer = atom(child(node, "layer"), 1, "F.Cu") or "F.Cu"
    at_node = child(node, "at")
    position = xy(at_node, f"{name} footprint position")
    angle = number(atom(at_node, 3, "0"), "footprint angle")
    reference = "<unknown>"
    for text_node in children(node, "fp_text"):
        if atom(text_node, 1) == "reference":
            reference = atom(text_node, 2, "<unknown>") or "<unknown>"
            break
    footprint = Footprint(name=name, ref=reference, layer=layer, at=position, angle=angle)
    for pad_node in children(node, "pad"):
        parsed = parse_pad(pad_node, footprint)
        if parsed is not None:
            footprint.pads.append(parsed)

    side_prefix = "B" if layer.startswith("B.") else "F"
    for outline_layer, source in (
        (f"{side_prefix}.CrtYd", "courtyard"),
        (f"{side_prefix}.Fab", "fabrication body"),
        (f"{side_prefix}.SilkS", "silkscreen body"),
    ):
        local_polygons = local_outline_polygons(node, outline_layer)
        if local_polygons:
            footprint.outlines = [
                [footprint_transform(point, footprint) for point in polygon]
                for polygon in local_polygons
            ]
            footprint.outline_source = source
            break
    return footprint


def parse_board(root: Sequence[SExpr]) -> tuple[list[Footprint], list[Polygon]]:
    if head(root) != "kicad_pcb":
        raise ParseError("top-level expression is not kicad_pcb")
    footprints = [parse_footprint(item) for item in children(root, "footprint")]
    board_polygons: list[Polygon] = []
    edge_lines: list[tuple[Point, Point]] = []
    for item in root[1:]:
        if not isinstance(item, list) or graphic_layer(item) != "Edge.Cuts":
            continue
        if head(item) == "gr_rect":
            board_polygons.append(rect_polygon(item))
        elif head(item) == "gr_circle":
            board_polygons.append(circle_polygon(item))
        elif head(item) == "gr_poly":
            polygon = poly_polygon(item)
            if len(polygon) >= 3:
                board_polygons.append(polygon)
        elif head(item) == "gr_line":
            edge_lines.append((xy(child(item, "start"), "edge start"), xy(child(item, "end"), "edge end")))
    board_polygons.extend(closed_line_polygons(edge_lines))
    if not board_polygons:
        raise ParseError("no closed Edge.Cuts polygon found")
    return footprints, board_polygons


def bounds(polygon: Polygon) -> tuple[float, float, float, float]:
    x_values = [point[0] for point in polygon]
    y_values = [point[1] for point in polygon]
    return (min(x_values), min(y_values), max(x_values), max(y_values))


def aabb_overlap(first: Polygon, second: Polygon, epsilon: float = EPSILON) -> bool:
    first_bounds = bounds(first)
    second_bounds = bounds(second)
    return (
        min(first_bounds[2], second_bounds[2])
        - max(first_bounds[0], second_bounds[0])
        > epsilon
        and min(first_bounds[3], second_bounds[3])
        - max(first_bounds[1], second_bounds[1])
        > epsilon
    )


def polygon_axes(polygon: Polygon) -> Iterator[Point]:
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        edge = (end[0] - start[0], end[1] - start[1])
        length = math.hypot(*edge)
        if length > EPSILON:
            yield (-edge[1] / length, edge[0] / length)


def project(polygon: Polygon, axis: Point) -> tuple[float, float]:
    values = [point[0] * axis[0] + point[1] * axis[1] for point in polygon]
    return (min(values), max(values))


def convex_polygons_overlap(first: Polygon, second: Polygon) -> bool:
    if not aabb_overlap(first, second):
        return False
    for axis in list(polygon_axes(first)) + list(polygon_axes(second)):
        first_projection = project(first, axis)
        second_projection = project(second, axis)
        if (
            min(first_projection[1], second_projection[1])
            - max(first_projection[0], second_projection[0])
            <= EPSILON
        ):
            return False
    return True


def signed_area(polygon: Polygon) -> float:
    return 0.5 * sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(polygon, polygon[1:] + polygon[:1])
    )


def cross(first: Point, second: Point, third: Point) -> float:
    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def point_in_triangle(point: Point, first: Point, second: Point, third: Point) -> bool:
    values = (cross(first, second, point), cross(second, third, point), cross(third, first, point))
    has_negative = any(value < -EPSILON for value in values)
    has_positive = any(value > EPSILON for value in values)
    return not (has_negative and has_positive)


def triangulate(polygon: Polygon) -> list[Polygon]:
    """Ear-clip a simple polygon so concave courtyards remain concave."""

    if len(polygon) < 3:
        return []
    points = polygon if signed_area(polygon) > 0 else list(reversed(polygon))
    remaining = list(range(len(points)))
    triangles: list[Polygon] = []
    guard = 0
    while len(remaining) > 3 and guard < len(points) * len(points):
        guard += 1
        clipped = False
        for offset, current in enumerate(remaining):
            previous = remaining[offset - 1]
            following = remaining[(offset + 1) % len(remaining)]
            first, second, third = points[previous], points[current], points[following]
            if cross(first, second, third) <= EPSILON:
                continue
            if any(
                point_in_triangle(points[candidate], first, second, third)
                for candidate in remaining
                if candidate not in {previous, current, following}
            ):
                continue
            triangles.append([first, second, third])
            remaining.pop(offset)
            clipped = True
            break
        if not clipped:
            # Repeated/collinear vertices can defeat strict ear clipping.  The
            # bounding hull is a conservative fallback and is surfaced only for
            # malformed outlines, never for ChainAxe's deliberate U1 L shape.
            return [
                [
                    (bounds(points)[0], bounds(points)[1]),
                    (bounds(points)[2], bounds(points)[1]),
                    (bounds(points)[2], bounds(points)[3]),
                    (bounds(points)[0], bounds(points)[3]),
                ]
            ]
    if len(remaining) == 3:
        triangles.append([points[index] for index in remaining])
    return triangles


def polygons_overlap(first: Polygon, second: Polygon) -> bool:
    if not aabb_overlap(first, second):
        return False
    return any(
        convex_polygons_overlap(first_triangle, second_triangle)
        for first_triangle in triangulate(first)
        for second_triangle in triangulate(second)
    )


def layers_intersect(first: frozenset[str], second: frozenset[str]) -> bool:
    return "*" in first or "*" in second or bool(first & second)


def pad_overlap_findings(footprints: Sequence[Footprint]) -> list[Finding]:
    copper_pads = [
        pad
        for footprint in footprints
        for pad in footprint.pads
        if pad.copper_layers and not pad.mechanical_hole
    ]
    holes = [
        pad
        for footprint in footprints
        for pad in footprint.pads
        if pad.mechanical_hole
    ]
    findings: list[Finding] = []
    for index, first in enumerate(copper_pads):
        for second in copper_pads[index + 1 :]:
            if first.ref == second.ref:
                continue
            if first.net == second.net:
                continue
            if not layers_intersect(first.copper_layers, second.copper_layers):
                continue
            if polygons_overlap(first.polygon, second.polygon):
                first_net = first.net if first.net is not None else "<no net>"
                second_net = second.net if second.net is not None else "<no net>"
                findings.append(
                    Finding(
                        "different-net pad overlap",
                        f"{first.label} [{first_net}] intersects {second.label} [{second_net}]",
                    )
                )
    for hole in holes:
        for pad in copper_pads:
            if hole.ref == pad.ref:
                continue
            if polygons_overlap(hole.polygon, pad.polygon):
                pad_net = pad.net if pad.net is not None else "<no net>"
                findings.append(
                    Finding(
                        "mechanical hole/copper overlap",
                        f"{hole.label} NPTH intersects {pad.label} [{pad_net}]",
                    )
                )
    return findings


def footprint_collision_findings(footprints: Sequence[Footprint]) -> list[Finding]:
    candidates = [
        footprint
        for footprint in footprints
        if footprint.outlines and not footprint.is_mounting_hole
    ]
    findings: list[Finding] = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            if first.layer[:1] != second.layer[:1]:
                continue
            if any(
                polygons_overlap(first_polygon, second_polygon)
                for first_polygon in first.outlines
                for second_polygon in second.outlines
            ):
                findings.append(
                    Finding(
                        "component outline collision",
                        f"{first.ref} ({first.outline_source}) intersects "
                        f"{second.ref} ({second.outline_source})",
                    )
                )
    return findings


def point_on_segment(point: Point, start: Point, end: Point) -> bool:
    if abs(cross(start, end, point)) > EPSILON:
        return False
    return (
        min(start[0], end[0]) - EPSILON <= point[0] <= max(start[0], end[0]) + EPSILON
        and min(start[1], end[1]) - EPSILON <= point[1] <= max(start[1], end[1]) + EPSILON
    )


def point_in_polygon(point: Point, polygon: Polygon, include_boundary: bool = True) -> bool:
    inside = False
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        if point_on_segment(point, start, end):
            return include_boundary
        if (start[1] > point[1]) != (end[1] > point[1]):
            intersection_x = (
                (end[0] - start[0]) * (point[1] - start[1]) / (end[1] - start[1])
                + start[0]
            )
            if point[0] < intersection_x:
                inside = not inside
    return inside


def outline_inside_board(outline: Polygon, board_polygons: Sequence[Polygon]) -> bool:
    return all(any(point_in_polygon(point, board) for board in board_polygons) for point in outline)


def edge_overhang_findings(
    footprints: Sequence[Footprint], board_polygons: Sequence[Polygon]
) -> list[Finding]:
    findings: list[Finding] = []
    for footprint in footprints:
        if (
            not footprint.outlines
            or footprint.is_mounting_hole
            or footprint.ref in DOCUMENTED_EDGE_OVERHANGS
        ):
            continue
        if any(not outline_inside_board(outline, board_polygons) for outline in footprint.outlines):
            findings.append(
                Finding(
                    "unexpected board-edge overhang",
                    f"{footprint.ref} {footprint.outline_source} crosses Edge.Cuts",
                )
            )
    return findings


def resolve_board_path(argument: pathlib.Path) -> pathlib.Path:
    if argument.is_file():
        return argument
    candidates = sorted(argument.glob("hardware/**/*.kicad_pcb"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"no .kicad_pcb found under {argument}")
    names = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"multiple .kicad_pcb files found; pass one explicitly: {names}")


def validate(board_path: pathlib.Path) -> tuple[list[Finding], int, int, int]:
    roots = parse_sexpr(board_path.read_text(encoding="utf-8"))
    if len(roots) != 1 or not isinstance(roots[0], list):
        raise ParseError("expected exactly one top-level PCB expression")
    footprints, board_polygons = parse_board(roots[0])
    findings = (
        pad_overlap_findings(footprints)
        + footprint_collision_findings(footprints)
        + edge_overhang_findings(footprints, board_polygons)
    )
    findings.sort(key=lambda finding: (finding.category, finding.message))
    pad_count = sum(
        1
        for footprint in footprints
        for pad in footprint.pads
        if pad.copper_layers and not pad.mechanical_hole
    )
    hole_count = sum(
        1 for footprint in footprints for pad in footprint.pads if pad.mechanical_hole
    )
    return findings, len(footprints), pad_count, hole_count


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=pathlib.Path,
        default=pathlib.Path("."),
        help="repository root or a specific .kicad_pcb file (default: .)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)
    try:
        board_path = resolve_board_path(arguments.path)
        findings, footprint_count, pad_count, hole_count = validate(board_path)
    except (OSError, ParseError) as exc:
        print(f"ERROR: PCB geometry validation could not run: {exc}", file=sys.stderr)
        return 2

    display_path = board_path.as_posix()
    print(
        f"PCB geometry: {display_path}: {footprint_count} footprints, "
        f"{pad_count} copper pads, {hole_count} NPTH/mechanical holes"
    )
    if findings:
        for finding in findings:
            print(f"ERROR [{finding.category}]: {finding.message}")
        print(f"PCB geometry validation failed with {len(findings)} error(s).")
        return 1
    print("PCB geometry validation passed (KiCad DRC and mechanical review still required).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
