"""Shared literal-source policy and escape/comment scanning for TeX fragments.

Restrictions protect the fixed fragment contract, not a complete TeX sandbox.
Compiler process and filesystem isolation remain the runtime security boundary.
"""

from __future__ import annotations

import string

_CONTROL_WORD_LETTERS = frozenset(string.ascii_letters)
_FORBIDDEN_TEX_CONTROL_WORDS = {
    **dict.fromkeys(
        (
            "closein closeout endinput font iffileexists include includegraphics "
            "input inputiffileexists lstinputlisting loadclass loadclasswithoptions "
            "newread newwrite openin openout pgfdeclareimage pgfimage read readline "
            "requirepackage requirepackagewithoptions usepackage verbatiminput "
            "xetexpdffile xetexpdfpagecount xetexpicfile"
        ).split(),
        "file access and resource loading belong to the fixed wrapper",
    ),
    **dict.fromkeys(
        (
            "directlua immediate pdfannot pdfcatalog pdfdest pdfextension pdffeedback "
            "pdfimage pdfliteral pdfobj pdfoutline pdfprimitive pdfrefobj pdfrefxform "
            "pdfrefximage pdfstartlink pdfxform pdfximage special typeout write"
        ).split(),
        "direct execution, output and low-level PDF operations are outside the fragment contract",
    ),
    **dict.fromkeys(
        (
            "catcode csname endcsname endlinechar escapechar expandafter "
            "explsyntaxon globaldefs makeatletter scantokens"
        ).split(),
        "dynamic tokenization and control names cannot be checked by the literal scanner",
    ),
}


def _is_escaped(source: str, index: int) -> bool:
    """Return whether the character at index follows an odd backslash run."""
    preceding_backslashes = 0
    cursor = index - 1
    while cursor >= 0 and source[cursor] == "\\":
        preceding_backslashes += 1
        cursor -= 1
    return preceding_backslashes % 2 == 1


def _without_tex_comments(source: str) -> str:
    """Blank TeX comments while retaining command boundaries and offsets."""
    characters = list(source)
    in_comment = False
    for index, character in enumerate(source):
        if in_comment:
            if character in "\r\n":
                in_comment = False
            else:
                characters[index] = " "
            continue
        if character != "%":
            continue
        if not _is_escaped(source, index):
            in_comment = True
            characters[index] = " "
    return "".join(characters)
