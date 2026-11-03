# The most important test file: composition strings in, parts / fibers / natural share out.
# Expected values were worked out by hand from the rules in the spec, not copied from parser output.
import re

import pytest

from quickshop.evidence.fabric import find_composition_text, parse_composition

# (id, raw text, confidence, main_part, natural_fiber_pct)
CASES = [
    # --- common formats
    ("percent-first", "60% Cotton, 40% Polyester", "explicit", "unspecified", 60.0),
    ("fiber-first-slash", "Cotton 60% / Polyester 40%", "explicit", "unspecified", 60.0),
    ("fiber-colon", "Cotton: 80%, Linen: 20%", "explicit", "unspecified", 100.0),
    ("no-separator", "95% cotton 5% elastane", "explicit", "unspecified", 95.0),
    ("single-fiber", "100% Cotton", "explicit", "unspecified", 100.0),
    ("uppercase", "100% COTTON", "explicit", "unspecified", 100.0),
    ("markdown-bold", "**Fabric:** 100% Cotton", "explicit", "unspecified", 100.0),
    ("one-per-line", "50% Cotton\n50% Linen", "explicit", "unspecified", 100.0),
    ("bullets", "- 70% Wool\n- 30% Nylon", "explicit", "unspecified", 70.0),
    ("header-word", "Composition: 60% Cotton / 40% Polyester", "explicit", "unspecified", 60.0),
    # --- real zero is different from unknown
    ("all-synthetic-is-zero-not-null", "100% Polyester", "explicit", "unspecified", 0.0),
    ("polyamide-elastane", "88% Polyamide, 12% Elastane", "explicit", "unspecified", 0.0),
    # --- parts
    ("shell-lining", "Shell: 100% Cotton. Lining: 100% Polyester", "explicit", "shell", 100.0),
    ("body-lining-semicolon", "Body: 100% Cotton; Lining: 100% Polyester", "explicit", "shell", 100.0),
    ("lining-listed-first", "Lining: 100% Polyester\nShell: 100% Cotton", "explicit", "shell", 100.0),
    ("outer-lining-slash", "Outer fabric: 100% Cotton / Lining: 65% Polyester, 35% Cotton", "explicit", "shell", 100.0),
    ("outer-with-blend", "Outer: 80% wool, 20% nylon; Lining: 100% viscose", "explicit", "shell", 80.0),
    ("parenthetical-labels", "100% cotton (shell), 100% polyester (lining)", "explicit", "shell", 100.0),
    ("body-and-sleeves", "Body 100% cotton, sleeves 100% polyester", "explicit", "shell", 100.0),
    ("trailing-label", "100% cotton body", "explicit", "shell", 100.0),
    ("label-on-own-line", "Shell:\n100% Cotton\nLining:\n100% Polyester", "explicit", "shell", 100.0),
    ("main-and-contrast", "Main fabric: 100% Polyester, Contrast: 100% Cotton", "explicit", "shell", 0.0),
    ("filling-ignored", "Shell: 100% cotton; Filling: 90% down, 10% feather", "explicit", "shell", 100.0),
    ("one-unlabelled-plus-lining", "100% Cotton\nLining: 100% Polyester", "explicit", "unspecified", 100.0),
    # --- synonyms and modifiers
    ("organic-cotton", "100% Organic Cotton", "explicit", "unspecified", 100.0),
    ("merino-wool", "100% Merino Wool", "explicit", "unspecified", 100.0),
    ("spandex", "98% Cotton, 2% Spandex", "explicit", "unspecified", 98.0),
    ("hemp-cotton", "55% Hemp 45% Cotton", "explicit", "unspecified", 100.0),
    ("silk-cashmere", "70% Cashmere 30% Silk", "explicit", "unspecified", 100.0),
    ("linen", "100% Linen", "explicit", "unspecified", 100.0),
    # --- regenerated cellulose: excluded from natural by default, reported separately
    ("rayon-default-excluded", "52% Rayon, 48% Cotton", "explicit", "unspecified", 48.0),
    ("viscose-polyester", "70% Viscose 30% Polyester", "explicit", "unspecified", 0.0),
    ("lyocell", "100% Tencel Lyocell", "explicit", "unspecified", 0.0),
    # --- other languages / repeated translations
    ("german", "97,5% Wolle, 2,5% Elasthan", "explicit", "unspecified", 97.5),
    ("repeated-translations", "60% Cotton, 40% Polyester\n60% Baumwolle, 40% Polyester\n60% Coton, 40% Polyester",
     "explicit", "unspecified", 60.0),
    # --- junk that must be handled
    ("care-text-after", "100% Cotton. Machine wash cold. Do not bleach.", "explicit", "unspecified", 100.0),
    ("care-text-mixed", "Composition: 60% Cotton / 40% Polyester. Wash at 30 degrees. Tumble dry low.",
     "explicit", "unspecified", 60.0),
    ("may-contain-ignored", "98% cotton 2% elastane. May contain traces of nylon 2%", "explicit", "unspecified", 98.0),
    # --- ambiguous: flagged, never rescaled, never guessed
    ("total-under-100-not-rescaled", "50% cotton, 30% polyester", "ambiguous", "unspecified", 50.0),
    ("total-over-100", "60% cotton 60% polyester", "ambiguous", "unspecified", None),
    ("approx", "approx. 60% cotton, 40% polyester", "ambiguous", "unspecified", 60.0),
    ("range", "55-60% cotton, 40% polyester", "ambiguous", "unspecified", None),
    ("unknown-fiber", "70% foo 30% cotton", "ambiguous", "unspecified", 30.0),
    ("lining-only", "Lining: 100% polyester", "ambiguous", None, None),
    ("two-unlabelled-different", "100% cotton\n100% polyester", "ambiguous", None, None),
    ("two-different-shells", "Shell: 60% cotton 40% polyester\nShell: 100% nylon", "ambiguous", None, None),
    ("fibers-without-percent", "cotton blend", "ambiguous", None, None),
    # --- nothing usable
    ("empty", "", "missing", None, None),
    ("whitespace", "   \n ", "missing", None, None),
    ("vague-marketing", "Premium denim", "missing", None, None),
    ("see-label", "See label for details", "missing", None, None),
    ("care-only", "Machine wash cold", "missing", None, None),
    ("percent-but-not-a-fiber", "100% recommend this product", "missing", None, None),
]


@pytest.mark.parametrize("raw,confidence,main,natural", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_composition_table(raw, confidence, main, natural):
    r = parse_composition(raw)
    assert r.confidence == confidence
    assert r.main_part == main
    assert r.natural_fiber_pct == natural


def test_none_input_is_missing_not_error():
    r = parse_composition(None)
    assert r.confidence == "missing" and r.natural_fiber_pct is None and r.components == []


def test_at_least_thirty_cases():
    assert len(CASES) >= 30


# --- regenerated cellulose flag
def test_regenerated_flag_on_counts_it_as_natural():
    assert parse_composition("52% Rayon, 48% Cotton", count_regenerated_as_natural=True).natural_fiber_pct == 100.0


def test_regenerated_is_always_reported_separately():
    r = parse_composition("52% Rayon, 48% Cotton")
    assert r.regenerated_fiber_pct == 52.0 and r.synthetic_fiber_pct == 0.0


def test_config_default_flag_is_off(monkeypatch):
    from quickshop.evidence import fiber_config
    assert fiber_config.COUNT_REGENERATED_AS_NATURAL is False
    monkeypatch.setattr(fiber_config, "COUNT_REGENERATED_AS_NATURAL", True)
    assert parse_composition("100% Modal").natural_fiber_pct == 100.0


# --- details of the output
def test_components_keep_part_and_original_text():
    r = parse_composition("Shell: 60% Organic Cotton, 40% Polyester. Lining: 100% Polyester")
    shell = next(c for c in r.components if c.part == "shell")
    assert [(f.fiber, f.percent, f.category) for f in shell.fibers] == [
        ("cotton", 60.0, "natural_plant"), ("polyester", 40.0, "synthetic")]
    assert shell.fibers[0].original == "60% Organic Cotton"
    assert next(c for c in r.components if c.part == "lining").fibers[0].fiber == "polyester"


def test_fiber_categories():
    cats = {f.fiber: f.category for f in parse_composition(
        "10% cotton 10% wool 10% viscose 10% nylon 10% acrylic 10% silk 10% linen 10% modal 10% cupro 10% elastane"
    ).components[0].fibers}
    assert cats == {"cotton": "natural_plant", "wool": "natural_animal", "viscose": "regenerated",
                    "nylon": "synthetic", "acrylic": "synthetic", "silk": "natural_animal",
                    "linen": "natural_plant", "modal": "regenerated", "cupro": "regenerated",
                    "elastane": "synthetic"}


def test_ambiguous_reasons_are_recorded():
    r = parse_composition("50% cotton, 30% polyester")
    assert any("under 100" in n for n in r.notes)


def test_status_property():
    assert parse_composition("100% cotton").status == "ok"
    assert parse_composition("cotton blend").status == "partial"


# --- every number reported must be traceable to the source text (fidelity)
@pytest.mark.parametrize("raw", [c[1] for c in CASES if c[1]], ids=[c[0] for c in CASES if c[1]])
def test_every_parsed_percent_appears_in_the_source(raw):
    numbers = {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", raw)}
    for comp in parse_composition(raw).components:
        for f in comp.fibers:
            assert f.percent in numbers, f"{f} not found in {raw!r}"


# --- finding composition in page markdown (fallback)
def test_find_composition_text_in_markdown():
    md = "# Shirt\n$58\n\n## Fabric\nMaterial: 55% Linen, 45% Cotton\nMachine wash.\n"
    text, blocks = find_composition_text(md)
    assert "55% Linen" in text and blocks == 1


def test_find_composition_keeps_label_lines():
    md = "Details\n\nShell:\n100% Cotton\nLining:\n100% Polyester\n\n\nReviews: 4 stars"
    text, _ = find_composition_text(md)
    assert parse_composition(text).main_part == "shell"


def test_find_composition_none_when_absent():
    assert find_composition_text("Great jeans, 4.9 stars, free shipping") == (None, 0)
    assert find_composition_text(None) == (None, 0)


def test_find_composition_counts_distinct_blocks():
    md = "100% Cotton tee\n\n\nYou may also like\n\n\n100% Polyester shorts"
    _, blocks = find_composition_text(md)
    assert blocks == 2
