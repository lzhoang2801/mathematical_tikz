"""Read a deliberately bounded notation grammar, not arbitrary prose semantics.

These obligations come from the instruction, independently of model quotations.
Unsupported quantitative expressions are retained as errors, never discarded.
"""
from __future__ import annotations

import re
import math

from spec_first.metric_expression import parse_measure

UNIT_CM = {'': 1.0, 'mm': .1, 'cm': 1.0, 'm': 100.0}
POINT = r"[A-Z](?:_[0-9]+|[0-9]+)?['\u2032\u2019]{0,2}"
SEGMENT = rf"({POINT})\s*({POINT})"
NUMBER = r"(?:\d+(?:\.\d+)?)(?:/\d+(?:\.\d+)?)?"
QUANTITY = re.compile(rf"({NUMBER})\s*(mm|cm|m)?")
CLAUSE_END = r"(?=[;,\n]|\.(?:\s|$)|\s+(?i:and|và)\s+|$)"
ASSIGNMENT = re.compile(rf"(?<![A-Za-z_']){SEGMENT}\s*=\s*(.+?){CLAUSE_END}")
FRACTION = rf"{POINT}\s*{POINT}\s*/\s*{POINT}\s*{POINT}"
FRACTION_CHAIN = re.compile(rf"(?<![\w'])({FRACTION}(?:\s*=\s*{FRACTION})*)\s*=\s*(.+?){CLAUSE_END}")
RADIUS = re.compile(rf"\(\s*({POINT})\s*;\s*([^;)]+)\)")
SHORTER = re.compile(rf"(?<![\w']){SEGMENT}\s*([<>])\s*{SEGMENT}(?![\w'])")
ANGLE = re.compile(rf"(?:∠|\\angle\s*|\b(?:góc|angle)\s+)({POINT})\s*({POINT})\s*({POINT})\s*=\s*(.+?){CLAUSE_END}", re.IGNORECASE)
SPATIAL = re.compile(r'\b(?:không gian|tứ diện|hình chóp|hình hộp|lăng trụ|mặt cầu|hình cầu|sphere|tetrahedron|pyramid|prism|parallelepiped)\b', re.IGNORECASE)
UNSUPPORTED_SURFACE = re.compile(r'\b(?:mặt cầu|hình cầu|hình trụ|hình nón|sphere|spherical|cylinder|cone)\b', re.IGNORECASE)
ANNOTATION = re.compile(r'\b(?:ghi|ghi rõ|đánh dấu|label|annotate)\b.*?\b(?:độ dài|lengths?)\b\s*(.*)', re.IGNORECASE)


PLANE = rf"\(\s*{POINT}(?:\s*{POINT}){{2,3}}\s*\)"
PLANE_PERP = re.compile(rf"({PLANE})\s*(?:⊥|\\perp|vuông góc (?:với\s*)?|perpendicular to\s*)({PLANE})", re.IGNORECASE)
PLANE_PERP_CHAIN = re.compile(rf"({PLANE})\s+(?:và|and)\s+({PLANE})\s+(?:cùng vuông góc với|are both perpendicular to)\s+({PLANE})", re.IGNORECASE)
DIHEDRAL = re.compile(rf"\[\s*({POINT})\s*[,;]\s*({POINT})\s*({POINT})\s*[,;]\s*({POINT})\s*\]\s*=\s*(.+?){CLAUSE_END}")


def assignment_prefix(instruction, start):
    prefix = instruction[:start].rstrip()
    return '' if re.search(r'\b(?:and|và)$', prefix, re.IGNORECASE) else prefix


def point_name(text):
    return text.replace('\u2032', "'").replace('\u2019', "'")


def number(text):
    parts = text.split('/')
    value = float(parts[0]) / (float(parts[1]) if len(parts) == 2 else 1)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Lengths and ratios must be positive')
    return value


def quantity_fields(text):
    numeric = QUANTITY.fullmatch(text.strip())
    if numeric:
        return {'value': number(numeric[1]), 'unit': numeric[2] or ''}
    match = re.fullmatch(r'(.+?)(?:\s+(mm|cm|m))?', text.strip())
    if not match:
        raise ValueError('Missing length quantity')
    parsed = parse_measure(match[1])
    if parsed.parameter and match[2]:
        raise ValueError('A symbolic length parameter already carries its dimension')
    return {'expression': match[1], 'unit': match[2] or ''}


def scan_instruction(instruction: str) -> dict:
    """Only explicit segment assignments, radius notation and inequalities.

    A successful scan establishes no coverage of other natural-language facts.
    The original spans and unparsed expressions are returned for admission logs.
    """
    obligations, issues = [], []
    for match in UNSUPPORTED_SURFACE.finditer(instruction):
        issues.append({'category': 'unsupported_representation', 'quote': match.group(),
                       'reason': 'The renderer has no curved spatial surface representation; a planar circle is not a substitute.'})
    def add(match, **fields):
        obligations.append({'quote': match.group(), 'span': list(match.span()), **fields})
    def add_planes(match, first, last):
        planes = [[point_name(n) for n in re.findall(POINT,text)] for text in (first,last)]
        add(match,kind='perpendicular_planes',points=planes[0][:3]+planes[1][:3])
        for plane in planes:
            if len(plane)==4:
                add(match,kind='on_plane',points=[plane[3],*plane[:3]])
    for match in PLANE_PERP.finditer(instruction):
        add_planes(match,match[1],match[2])
    for match in PLANE_PERP_CHAIN.finditer(instruction):
        add_planes(match,match[1],match[3])
        add_planes(match,match[2],match[3])
    for match in DIHEDRAL.finditer(instruction):
        prefix=assignment_prefix(instruction,match.start())
        if (re.search(r"(?:[+\-*/=^×÷−·°)\]}\d]|\\(?:times|cdot|div))$",prefix)
                or re.search(r'(?:^|[^\w])(?:[A-Za-z]|sin|cos|tan|cot|sec|csc|sqrt|frac)$',prefix)):
            issues.append({'category':'unsupported_metric','quote':match.group(),'reason':'A dihedral assignment cannot be a suffix of another expression.'})
            continue
        value=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:°|degrees?)',match[5].strip())
        if not value or not 0 < float(value[1]) < 180:
            issues.append({'category':'unsupported_metric','quote':match.group(),'reason':'A nondegenerate dihedral requires 0 < angle < 180.'})
        else:
            add(match,kind='dihedral_angle',points=[point_name(match[i]) for i in (1,2,3,4)],value=float(value[1]))
    for match in RADIUS.finditer(instruction):
        radius_segment = re.fullmatch(SEGMENT, match[2].strip())
        if radius_segment:
            add(match, kind='radius_segment', center=point_name(match[1]),
                points=[point_name(radius_segment[1]), point_name(radius_segment[2])], value=1.0)
        else:
            try:
                add(match, kind='radius', center=point_name(match[1]), **quantity_fields(match[2]))
            except (ValueError, ZeroDivisionError) as error:
                issues.append({'category': 'unsupported_metric', 'quote': match.group(), 'reason': str(error)})
    angle_spans = []
    for match in ANGLE.finditer(instruction):
        angle_spans.append(match.span())
        prefix = assignment_prefix(instruction,match.start())
        if (re.search(r"(?:[+\-*/=^×÷−·°)\]}\d]|\\(?:times|cdot|div))$", prefix)
                or re.search(r'(?:^|[^\w])(?:[A-Za-z]|sin|cos|tan|cot|sec|csc|sqrt|frac)$', prefix)
                or re.match(r',\s*\d', instruction[match.end():])):
            issues.append({'category':'unsupported_metric','quote':match.group(), 'reason':'A fixed angle cannot be a suffix of another expression or a truncated quantity.'})
            continue
        value = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:°|degrees?)', match[4].strip())
        if not value or not 0 < float(value[1]) < 180:
            issues.append({'category':'unsupported_metric', 'quote':match.group(), 'reason':'A fixed angle needs a complete degree value strictly between 0 and 180.'})
        else:
            add(match, kind='angle', points=[point_name(match[i]) for i in (1,2,3)], value=float(value[1]))
    fraction_spans = []
    for match in FRACTION_CHAIN.finditer(instruction):
        fraction_spans.append(match.span())
        prefix = assignment_prefix(instruction,match.start())
        if re.search(r"(?:[+\-*/=^\u00d7\u00f7\u2212\u00b7)\]}\d]|[A-Z]['\u2032\u2019]*|\\(?:times|cdot|div))$",prefix):
            issues.append({'category':'unsupported_metric','quote':match.group(),
                           'reason':'The fraction is a suffix of an unsupported left-hand expression.'})
            continue
        if re.match(r',\s*\d',instruction[match.end():]):
            issues.append({'category':'unsupported_metric','quote':match.group(),
                           'reason':'A decimal comma or numeric continuation cannot be truncated.'})
            continue
        if not re.fullmatch(NUMBER,match[2].strip()):
            issues.append({'category':'unsupported_metric','quote':match.group(),
                           'reason':'A segment-fraction chain requires one complete positive numeric ratio.'})
            continue
        try:
            value = number(match[2].strip())
        except (ValueError,ZeroDivisionError) as error:
            issues.append({'category':'invalid_metric','quote':match.group(),'reason':str(error)})
            continue
        for fraction in re.finditer(rf"{SEGMENT}\s*/\s*{SEGMENT}",match[1]):
            add(match,kind='length_ratio',points=[point_name(n) for n in fraction.groups()],value=value)
    for match in ASSIGNMENT.finditer(instruction):
        # A denominator followed by '=' belongs to the enclosing ratio chain,
        # not a separate segment-length assignment.
        if any(lo <= match.start() < hi for lo,hi in fraction_spans+angle_spans):
            continue
        prefix = assignment_prefix(instruction,match.start())
        if re.search(r"(?:[+\-*/=^×÷−·)\]}\d]|[A-Z]['′’]*|\\(?:times|cdot|div))$", prefix) or re.match(r',\s*\d', instruction[match.end():]):
            issues.append({'category':'unsupported_metric','quote':match.group(), 'reason':'A metric expression cannot be truncated to a segment assignment.'})
            continue
        parts = [p.strip() for p in match[3].split('=')]
        expression = parts[-1]
        ratio = re.fullmatch(rf"({NUMBER})?\s*{SEGMENT}", expression)
        segments = [[point_name(match[1]), point_name(match[2])]]
        try:
            for part in parts[:-1]:
                segment = re.fullmatch(SEGMENT, part)
                if not segment:
                    raise ValueError('Every intermediate equality must be a complete segment')
                segments.append([point_name(segment[1]), point_name(segment[2])])
            if ratio:
                for endpoints in segments:
                    add(match, kind='length_ratio', points=endpoints + [point_name(ratio[2]), point_name(ratio[3])],
                        value=number(ratio[1]) if ratio[1] else 1.0)
            else:
                fields = quantity_fields(expression)
                for endpoints in segments:
                    add(match, kind='length', points=endpoints, **fields)
        except (ValueError, ZeroDivisionError) as error:
            issues.append({'category': 'invalid_metric', 'quote': match.group(), 'reason': str(error)})
    for match in SHORTER.finditer(instruction):
        left = [point_name(match[1]), point_name(match[2])]
        right = [point_name(match[4]), point_name(match[5])]
        add(match, kind='shorter', points=left+right if match[3] == '<' else right+left)
    annotations, unparsed_annotations = [], []
    for clause in re.split(r'[;\n]|\.(?=\s|$)', instruction):
        annotation = ANNOTATION.search(clause)
        if annotation:
            expression = re.sub(r'\s+(?:tương ứng trên hình|trên hình|respectively(?: on the diagram)?|on the diagram)\s*$', '', annotation[1], flags=re.IGNORECASE).strip()
            # This reader owns explicit quantity lists, not prose such as
            # "label the given lengths". Keep that prose visible to the model
            # and audit instead of misclassifying it as a malformed number.
            word = re.match(r'([^\W\d_]+)\b', expression)
            if (word and len(word[1]) > 1 and word[1].lower() != 'sqrt'
                    and not re.match(r'\s*[(/+*^=]', expression[word.end():])):
                unparsed_annotations.append({'quote':clause.strip(),'reason':'Prose annotation request; numeric-list admission does not establish its coverage.'})
                continue
            parts = re.split(r'\s*,\s*(?:(?:and|và)\s+)?|\s+(?:and|và)\s+', expression, flags=re.IGNORECASE) if expression else []
            try:
                quantities = [quantity_fields(part) for part in parts]
            except (ValueError, ZeroDivisionError) as error:
                issues.append({'category':'unsupported_annotation', 'quote':clause.strip(), 'reason':str(error)})
                continue
            annotations.append({'quote': clause.strip(), 'quantities': quantities})
    if obligations and re.search(r'\b(?:chứng minh|prove|show that)\b', instruction, re.IGNORECASE):
        issues.append({'category': 'unsupported_goal_scope', 'quote': instruction,
                       'reason': 'Given quantities cannot be separated from proof goals by this bounded notation reader.'})
    return {'obligations': obligations, 'annotations': annotations, 'unparsed_annotations': unparsed_annotations, 'issues': issues,
            'spatial_requested': bool(SPATIAL.search(instruction)),
            'coverage': 'Explicit notation only; not a certificate of full instruction fidelity.'}
