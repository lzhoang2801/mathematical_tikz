"""Small, total parser for positive lengths: constants or one shared scale.

No Python/TeX evaluation. A symbol denotes a positive length parameter, never a
number chosen by the model. Products of lengths, mixed parameters and mixed
dimensions are rejected. The generated TeX uses only this parser's vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
import re


@dataclass(frozen=True)
class Measure:
    coefficient: float
    parameter: str
    tex: str
    uncertainty: float = 0.0


@lru_cache(maxsize=512)
def parse_measure(expression: str) -> Measure:
    if not expression or len(expression) > 160:
        raise ValueError('Length expression must contain 1 to 160 characters')
    text = expression.replace('√', 'sqrt').replace('−', '-').replace('×', '*').replace('·', '*')
    text = text.replace(r'\sqrt', 'sqrt').replace(r'\frac', 'frac')
    text = re.sub(r'\s+', '', text)
    tokens = re.findall(r'\d+(?:\.\d+)?|sqrt|frac|[A-Za-z]|[()+*/{}-]', text)
    if ''.join(tokens) != text or len(tokens) > 64:
        raise ValueError('Unsupported or overlong length expression')
    position = 0

    def bounded(value):
        if not math.isfinite(value.coefficient) or abs(value.coefficient) > 1e12:
            raise ValueError('Length coefficient is outside finite bounds')
        return value

    def combine(left, right, op):
        a, b = left.coefficient, right.coefficient
        if op in '+-':
            if left.parameter != right.parameter:
                raise ValueError('Cannot add different length parameters or dimensions')
            result = a+b if op == '+' else a-b
            return bounded(Measure(result, left.parameter,
                                   rf'\left({left.tex}{op}{right.tex}\right)',
                                   left.uncertainty+right.uncertainty+2*math.ulp(result)))
        if op == '*':
            if left.parameter and right.parameter:
                raise ValueError('Products of length parameters are not lengths')
            error = abs(a)*right.uncertainty+abs(b)*left.uncertainty+left.uncertainty*right.uncertainty+2*math.ulp(a*b)
            return bounded(Measure(a*b, left.parameter or right.parameter, rf'{left.tex}\,{right.tex}', error))
        if right.parameter or abs(b) <= right.uncertainty:
            raise ValueError('Length denominator must be a nonzero constant')
        error = (left.uncertainty+abs(a/b)*right.uncertainty)/(abs(b)-right.uncertainty)+2*math.ulp(a/b)
        return bounded(Measure(a/b, left.parameter, rf'\frac{{{left.tex}}}{{{right.tex}}}', error))

    def atom(depth):
        nonlocal position
        if depth > 12 or position >= len(tokens):
            raise ValueError('Incomplete or excessively nested length expression')
        token = tokens[position]
        position += 1
        if token in ('(', '{'):
            value = expression_at(depth+1)
            closing = ')' if token == '(' else '}'
            if position >= len(tokens) or tokens[position] != closing:
                raise ValueError('Unbalanced length expression')
            position += 1
            return value
        if token in ('+', '-'):
            value = atom(depth+1)
            return Measure(value.coefficient * (-1 if token == '-' else 1), value.parameter,
                           rf'\left({token}{value.tex}\right)', value.uncertainty)
        if token == 'sqrt':
            value = atom(depth+1)
            if value.parameter or value.coefficient < value.uncertainty:
                if not value.parameter and value.coefficient == value.uncertainty == 0:
                    return Measure(0, '', r'\sqrt{0}')
                raise ValueError('Square roots require a nonnegative constant')
            root = math.sqrt(value.coefficient)
            error = max(root-math.sqrt(max(0,value.coefficient-value.uncertainty)),
                        math.sqrt(value.coefficient+value.uncertainty)-root)+2*math.ulp(root)
            return bounded(Measure(root, '', rf'\sqrt{{{value.tex}}}', error))
        if token == 'frac':
            if position >= len(tokens) or tokens[position] != '{':
                raise ValueError('frac requires two braced arguments')
            numerator = atom(depth+1)
            if position >= len(tokens) or tokens[position] != '{':
                raise ValueError('frac requires two braced arguments')
            return combine(numerator, atom(depth+1), '/')
        if re.fullmatch(r'\d+(?:\.\d+)?', token):
            value = float(token)
            return bounded(Measure(value, '', token, math.ulp(value) if value else 0))
        if re.fullmatch('[A-Za-z]', token):
            return Measure(1.0, token, token)
        raise ValueError('Expected a length expression atom')

    def product(depth):
        nonlocal position
        left = atom(depth)
        while position < len(tokens):
            token = tokens[position]
            if token in ('*', '/'):
                position += 1
                left = combine(left, atom(depth+1), token)
            elif token in ('sqrt', 'frac', '(', '{') or re.fullmatch('[A-Za-z]', token):
                left = combine(left, atom(depth+1), '*')
            else:
                break
        return left

    def expression_at(depth):
        nonlocal position
        left = product(depth)
        while position < len(tokens) and tokens[position] in ('+', '-'):
            op = tokens[position]
            position += 1
            left = combine(left, product(depth+1), op)
        return left

    result = expression_at(0)
    if (position != len(tokens) or result.coefficient <= result.uncertainty
            or result.uncertainty > result.coefficient*1e-10):
        raise ValueError('Length expression must be complete, positive and numerically resolved; cancellation cannot define a reliable scale')
    return result


def metric_measure(item) -> Measure:
    """Read a relation or label; schema validation owns mutually exclusive fields."""
    if item.expression:
        return parse_measure(item.expression)
    value = item.values[0] if hasattr(item, 'values') else item.value
    return Measure(value, '', format(value, '.12g'))
