"""
tests/test_knowledge_validation.py
===================================
The knowledge base must fail loudly on a broken file, not silently mis-score.

``rule_engine/validator.py``'s original checks (``validate_ruleset``,
``find_contradictory_rules``, etc.) were audited as never being called at
runtime against ``rule_engine/rules/rules.json`` - nothing in ``engine.py``,
``predictor.py`` or ``app_rule.py`` imported them. The same would have been
true of the new knowledge base had nothing changed: ``KnowledgeBase.load()``
previously only checked that ``families`` was non-empty.

``validate_knowledge_base`` closes that gap for the new format, and
``KnowledgeBase.load()`` now calls it before returning. A discriminator naming
an element or ratio that does not exist in that family's own data is exactly
the kind of authoring mistake that should raise at load time - left
unvalidated, it would silently contribute zero evidence for that term instead
of the intended signal, wrong and quiet about it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rule_engine.scoring import KnowledgeBase, get_knowledge_base  # noqa: E402
from rule_engine.validator import validate_knowledge_base  # noqa: E402


def _minimal_family(**overrides) -> dict:
    base = {
        "label": "Test family",
        "elements": {"Fe": {"band_wt": [90.0, 99.0]}},
        "discriminators": [],
        "ratios": [],
        "components": ["Widget"],
    }
    base.update(overrides)
    return base


def test_the_shipped_knowledge_base_is_valid():
    """The file actually used in production must pass its own schema check."""
    data = json.loads(
        (ROOT / "rule_engine" / "knowledge" / "materials.json").read_text(
            encoding="utf-8"
        )
    )
    report = validate_knowledge_base(data)
    assert report["is_valid"], report["issues"]


def test_load_succeeds_on_the_shipped_file():
    """get_knowledge_base() must not raise on the real, current knowledge base."""
    kb = get_knowledge_base()
    assert len(kb.families) > 0


@pytest.mark.parametrize(
    "label,families",
    [
        ("empty families dict", {}),
        (
            "band lo greater than hi",
            {"F1": _minimal_family(elements={"Fe": {"band_wt": [99.0, 90.0]}})},
        ),
        (
            "discriminator not in this family's elements",
            {"F1": _minimal_family(discriminators=["Cr"])},
        ),
        (
            "ratio discriminator with no matching ratio entry",
            {"F1": _minimal_family(discriminators=["Sn/Cu"], ratios=[])},
        ),
        (
            "ratio min greater than max",
            {
                "F1": _minimal_family(
                    discriminators=["Sn/Cu"],
                    ratios=[{"ratio": "Sn/Cu", "min": 0.5, "max": 0.1}],
                )
            },
        ),
        ("family entry is not a dict", {"F1": "not a dict"}),
    ],
)
def test_broken_knowledge_base_is_rejected(label, families):
    report = validate_knowledge_base({"families": families})
    assert report["is_valid"] is False, label
    assert report["issues"], label + ": expected at least one issue"


def test_load_raises_on_a_broken_file(tmp_path):
    """KnowledgeBase.load() must refuse to start on a structurally broken file.

    This is the load-time gate itself, not just the underlying check.
    """
    broken = {
        "families": {
            "F1": _minimal_family(elements={"Fe": {"band_wt": [99.0, 1.0]}})
        }
    }
    path = tmp_path / "broken_materials.json"
    path.write_text(json.dumps(broken), encoding="utf-8")

    with pytest.raises(ValueError, match="failed validation"):
        KnowledgeBase.load(path)


def test_a_valid_minimal_file_loads_successfully(tmp_path):
    """The gate must not be so strict it rejects a legitimately small file."""
    minimal = {"families": {"F1": _minimal_family()}}
    path = tmp_path / "minimal_materials.json"
    path.write_text(json.dumps(minimal), encoding="utf-8")

    kb = KnowledgeBase.load(path)
    assert "F1" in kb.families


def test_valid_ratio_discriminator_is_accepted():
    """A discriminator naming a ratio WITH a matching entry must pass."""
    families = {
        "F6": _minimal_family(
            discriminators=["Sn/Cu"],
            ratios=[{"ratio": "Sn/Cu", "min": 0.04, "max": 0.16}],
        )
    }
    report = validate_knowledge_base({"families": families})
    assert report["is_valid"], report["issues"]


def test_missing_candidate_components_is_a_warning_not_an_error():
    """A family with no listed components is unusual but not structurally broken."""
    families = {"F1": _minimal_family(components=[])}
    report = validate_knowledge_base({"families": families})
    assert report["is_valid"] is True
    assert any("no candidate components" in w for w in report["warnings"])
