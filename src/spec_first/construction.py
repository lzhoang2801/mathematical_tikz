"""Bounded planar constructions for the experimental drawing tool.

This is a forward executor, not a constraint solver. The model still chooses
constructions and visible content; downstream checks establish source fidelity.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

Name = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9]{0,23}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(StrictModel):
    name: Name
    op: Literal["free", "lerp", "project", "reflect", "intersect", "rotate"]
    refs: list[Name] = Field(default_factory=list, max_length=4, description="Earlier point names. free: []; lerp: [A,B]; project/reflect: [P,A,B] onto/across line AB; intersect: [A,B,C,D] for lines AB/CD; rotate: [O,P] about O.")
    values: list[FiniteFloat] = Field(default_factory=list, max_length=2, description="free: [x,y] in cm; lerp: [t] for A+t(B-A); rotate: [counterclockwise degrees]; others: [].")


class Segment(StrictModel):
    a: Name
    b: Name
    dashed: bool = False
    arrow: bool = False
    ticks: int = Field(default=0, ge=0, le=3, description="0 for no equality mark; 1/2/3 for equal-length classes. Matching nonzero values must have equal lengths.")


class Circle(StrictModel):
    center: Name
    through: Name


class Angle(StrictModel):
    a: Name
    vertex: Name
    b: Name
    kind: Literal["right", "equal"]
    group: int = Field(default=1, ge=1, le=3, description="For equal angles: equality class and arc count. Minor sector is selected deterministically.")


class Label(StrictModel):
    point: Name
    text: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9]{0,15}'{0,2}$", description="Math label such as A, B', x or d. No TeX commands.")
    position: Literal["above", "below", "left", "right", "above left", "above right", "below left", "below right"]
    dot: bool = True


class Construction(StrictModel):
    points: list[Point] = Field(min_length=2, max_length=32)
    segments: list[Segment] = Field(default_factory=list, max_length=64)
    circles: list[Circle] = Field(default_factory=list, max_length=8)
    angles: list[Angle] = Field(default_factory=list, max_length=24)
    labels: list[Label] = Field(min_length=1, max_length=32)
    scale: FiniteFloat = Field(default=1.0, ge=0.25, le=3)


def realize(plan: Construction) -> tuple[str, dict[str, tuple[float, float]]]:
    """Validate dependencies/degeneracy/mark truth, then emit named PGF operations."""
    points: dict[str, tuple[float, float]] = {}
    free, derived, strokes, labels = [], [], [], []
    lengths, angles = defaultdict(list), defaultdict(list)

    def point(name):
        if name not in points:
            raise ValueError(f"Unknown or forward point reference: {name}")
        return points[name]

    def vector(a, b):
        p, q = point(a), point(b)
        return q[0] - p[0], q[1] - p[1]

    def length(a, b):
        value = math.hypot(*vector(a, b))
        if value < 1e-7:
            raise ValueError(f"Degenerate carrier {a}--{b}")
        return value

    def fmt(value):
        return format(0.0 if abs(value) < 1e-12 else value, ".12g")

    arity = {"free": (0, 2), "lerp": (2, 1), "project": (3, 0), "reflect": (3, 0), "intersect": (4, 0), "rotate": (2, 1)}
    for step in plan.points:
        name, refs, values = step.name, step.refs, step.values
        if name in points or name.startswith("ConstructionFoot"):
            raise ValueError(f"Duplicate or reserved point name: {name}")
        if (len(refs), len(values)) != arity[step.op]:
            raise ValueError(f"Wrong arity for {step.op}: expected refs/values {arity[step.op]}")
        for ref in refs:
            point(ref)
        if step.op == "free":
            xy = tuple(values)
            expression = f"{fmt(xy[0])},{fmt(xy[1])}"
        elif step.op == "lerp":
            a, b = refs
            length(a, b)
            t = values[0]
            xy = tuple(p + t * v for p, v in zip(point(a), vector(a, b)))
            expression = f"$({a})!{fmt(t)}!({b})$"
        elif step.op in {"project", "reflect"}:
            p, a, b = refs
            size = length(a, b)
            v, w = vector(a, b), vector(a, p)
            t = sum(u * v for u, v in zip(v, w)) / size**2
            foot = tuple(x + t * y for x, y in zip(point(a), v))
            if step.op == "project":
                xy = foot
                expression = f"$({a})!({p})!({b})$"
            else:
                xy = tuple(2 * x - y for x, y in zip(foot, point(p)))
                helper = "ConstructionFoot" + name
                derived.append(f"  \\coordinate ({helper}) at ($({a})!({p})!({b})$);")
                expression = f"$({p})!2!({helper})$"
        elif step.op == "intersect":
            a, b, c, d = refs
            size = length(a, b) * length(c, d)
            u, v, w = vector(a, b), vector(c, d), vector(a, c)
            determinant = u[0] * v[1] - u[1] * v[0]
            if abs(determinant) <= 1e-7 * size:
                raise ValueError(f"Parallel or ill-conditioned intersection at {name}")
            t = (w[0] * v[1] - w[1] * v[0]) / determinant
            xy = tuple(p + t * v for p, v in zip(point(a), u))
            expression = f"intersection of {a}--{b} and {c}--{d}"
        else:
            o, p = refs
            length(o, p)
            angle = values[0]
            if abs(angle) > 360:
                raise ValueError("Rotation must be between -360 and 360 degrees")
            theta = math.radians(angle)
            x, y = vector(o, p)
            ox, oy = point(o)
            xy = ox + x * math.cos(theta) - y * math.sin(theta), oy + x * math.sin(theta) + y * math.cos(theta)
            expression = f"$({o})!1!{fmt(angle)}:({p})$"
        if not all(math.isfinite(v) and abs(v) <= 50 for v in xy):
            raise ValueError(f"Point {name} is nonfinite or outside the pilot's 50 cm frame")
        points[name] = xy
        (free if step.op == "free" else derived).append(f"  \\coordinate ({name}) at ({expression});")

    seen_segments = set()
    for segment in plan.segments:
        a, b = segment.a, segment.b
        size = length(a, b)
        key = tuple(sorted((a, b)))
        if key in seen_segments:
            raise ValueError(f"Duplicate drawn segment {a}--{b}")
        seen_segments.add(key)
        if segment.ticks:
            lengths[segment.ticks].append(size)
        options = [option for enabled, option in ((segment.dashed, "dashed"), (segment.arrow, "->")) if enabled]
        tick = "node[midway,sloped] {$" + "|" * segment.ticks + "$} " if segment.ticks else ""
        strokes.append(f"  \\draw[{','.join(options)}] ({a})--{tick}({b});")
    for circle in plan.circles:
        length(circle.center, circle.through)
        strokes.append(f"  \\node[draw,circle through=({circle.through})] at ({circle.center}) {{}};")
    for mark in plan.angles:
        a, v, b = mark.a, mark.vertex, mark.b
        size = length(v, a) * length(v, b)
        u, w = vector(v, a), vector(v, b)
        cosine = sum(x * y for x, y in zip(u, w)) / size
        angle = math.acos(max(-1, min(1, cosine)))
        if min(angle, math.pi - angle) < 1e-7:
            raise ValueError(f"Degenerate angle {a}--{v}--{b}")
        if u[0] * w[1] - u[1] * w[0] < 0:
            a, b = b, a
        if mark.kind == "right":
            if abs(cosine) > 1e-6:
                raise ValueError(f"False right-angle mark {a}--{v}--{b}")
            radii, kind = [5], "right angle"
        else:
            angles[mark.group].append(angle)
            radii, kind = [7 + 2 * i for i in range(mark.group)], "angle"
        for radius in radii:
            strokes.append(f"  \\pic[draw,angle radius={radius}pt] {{{kind}={a}--{v}--{b}}};")
    for kind, groups in (("length", lengths), ("angle", angles)):
        for group, values in groups.items():
            if len(values) < 2 or any(not math.isclose(v, values[0], rel_tol=1e-6, abs_tol=1e-7) for v in values):
                raise ValueError(f"Invalid {kind} equality class {group}: {values}")
    seen_labels = set()
    for label in plan.labels:
        point(label.point)
        if label.text in seen_labels:
            raise ValueError(f"Duplicate visible label: {label.text}")
        seen_labels.add(label.text)
        if label.dot:
            labels.append(f"  \\node[circle,fill,inner sep=1.35pt,label={{{label.position}:${label.text}$}}] at ({label.point}) {{}};")
        else:
            labels.append(f"  \\node[{label.position}] at ({label.point}) {{${label.text}$}};")
    if not strokes:
        raise ValueError("At least one visible carrier is required")
    source = [f"\\begin{{tikzpicture}}[scale={fmt(plan.scale)},thick,line cap=round,line join=round,font=\\footnotesize,label distance=2pt]",
              r"  \begin{pgfinterruptboundingbox}", *free, "", *derived, r"  \end{pgfinterruptboundingbox}", "", *strokes, "", *labels, r"\end{tikzpicture}"]
    return "\n".join(source), points
