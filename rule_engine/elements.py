"""
rule_engine/elements.py
=======================
Standard chemical element symbols (Z = 1..118) and element symbol canonicalizer.
Pure Python standard library with zero dependencies.
"""

from __future__ import annotations

import re
from typing import Optional

#: All standard chemical element symbols (Z = 1..118).
ELEMENT_SYMBOLS = frozenset({
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al",
    "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
    "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W",
    "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf",
    "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
})


def canonical_element_symbol(tok: str) -> Optional[str]:
    """
    Return the canonical element symbol for a header token, or None if the
    token isn't a recognised element symbol. Handles tokens carrying stray
    annotations like 'Cu(wt%)', 'Fe%', 'O ' etc., and accepts case variants
    such as 'FE' / 'fe'.

    Compound formulae are deliberately rejected rather than reduced to their
    leading element: an 'Al2O3' or 'FeO' column reports the wt% of the
    *oxide*, which is not the wt% of Al or Fe (Al is only ~52.9% of Al2O3 by
    mass), so silently treating it as the bare element would corrupt the
    composition.
    """
    stripped = tok.strip()
    # A multi-word phrase is never an element symbol.
    if re.search(r"\s", stripped):
        return None
    # Cut at the first annotation separator, so 'Cu(wt%)' -> 'Cu'.
    head = re.split(r"[(\[{<%/,;:|]", stripped, maxsplit=1)[0]
    # Element symbols are purely alphabetic; a digit means a compound formula.
    if not head or any(ch.isdigit() for ch in head):
        return None
    bare = re.sub(r"[^A-Za-z]", "", head)
    if not bare:
        return None
    if bare in ELEMENT_SYMBOLS:
        return bare
    titled = bare[:1].upper() + bare[1:].lower()
    if titled in ELEMENT_SYMBOLS:
        return titled
    return None
