# Deterministic fabric parser. Pure functions, no network, no LLM.
# Input: the composition text exactly as the page wrote it. Output: parts, normalized fibers,
# and natural_fiber_pct for the MAIN fabric only. Nothing is guessed or rescaled.
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from quickshop.evidence import fiber_config as cfg
from quickshop.evidence.schema import Component, FiberShare

NATURAL_CATEGORIES = {"natural_plant", "natural_animal"}

_WORD = r"[^\W\d_]+(?:[-'’][^\W\d_]+)*"
_NUM = r"\d+(?:[.,]\d+)?"
_PCT_RE = re.compile(
    rf"(?P<lo>{_NUM})(?:\s*(?:-|–|—|to)\s*(?P<hi>{_NUM}))?\s*(?:%|percent\b|per\s*cent\b)",
    re.IGNORECASE,
)
_WORD_RE = re.compile(_WORD)
_DELIMS = ",;/&()[]{}|:\n.•·"
_APPROX_RE = re.compile(r"\b(?:approx(?:imately)?\.?|circa|roughly|around|about)\b|~", re.IGNORECASE)
_MAY_CONTAIN_RE = re.compile(
    r"\b(?:may|might|can|could)\s+contain\b[^\n.;]*|\btraces?\s+of\b[^\n.;]*|\bcontains?\s+traces\b[^\n.;]*",
    re.IGNORECASE,
)

_ALIASES = cfg.FIBER_ALIASES
_LABEL_ALTS = "|".join(re.escape(k) for k in sorted(cfg.PART_ALIASES, key=len, reverse=True))
_LABEL_RE = re.compile(rf"(?<!\w)(?P<label>{_LABEL_ALTS})(?!\w)\s*[:\-–=]?", re.IGNORECASE)
_PAREN_LABEL_RE = re.compile(rf"\(\s*(?P<label>{_LABEL_ALTS})\s*\)", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"\n+|;|(?<=[A-Za-z%\)])\.\s+(?=[A-ZÀ-Ý])")


@dataclass
class ParsedComposition:
    components: list[Component] = field(default_factory=list)
    main_part: str | None = None
    natural_fiber_pct: float | None = None
    regenerated_fiber_pct: float | None = None
    synthetic_fiber_pct: float | None = None
    unknown_fiber_pct: float | None = None
    confidence: str = "missing"            # explicit | ambiguous | missing
    notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "ok" if self.confidence == "explicit" else "partial"


@dataclass
class _Seg:
    part: str | None
    text: str
    pairs: list[FiberShare] = field(default_factory=list)


# ---------------------------------------------------------------- fiber lookup

def _lookup(words: list[str]) -> str | None:
    """Canonical fiber for a list of words, or None. Modifier words are ignored."""
    words = [w.lower().strip("-'’") for w in words if w.strip("-'’")]
    if not words:
        return None
    full = " ".join(words)
    if full in _ALIASES:
        return _ALIASES[full]
    core = [w for w in words if w not in cfg.FIBER_MODIFIERS]
    if core and core != words:
        key = " ".join(core)
        if key in _ALIASES:
            return _ALIASES[key]
    return None


def _words(text: str, offset: int = 0) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start() + offset, m.end() + offset) for m in _WORD_RE.finditer(text)]


def _resolve_forward(ws):
    """Fiber that FOLLOWS a percent ("60% organic cotton"). Returns (canonical, category, start, end)."""
    for n in range(min(4, len(ws)), 0, -1):
        canon = _lookup([w[0] for w in ws[:n]])
        if canon:
            return canon, cfg.FIBER_CATEGORY[canon], ws[0][1], ws[n - 1][2]
    return _unknown(ws[:1])


def _resolve_backward(ws):
    """Fiber that PRECEDES a percent ("organic cotton 60%")."""
    for n in range(min(4, len(ws)), 0, -1):
        canon = _lookup([w[0] for w in ws[-n:]])
        if canon:
            return canon, cfg.FIBER_CATEGORY[canon], ws[-n][1], ws[-1][2]
    return _unknown(ws[-1:])


def _unknown(ws):
    if not ws:
        return None
    word, a, b = ws[0]
    w = word.lower()
    if len(w) < 3 or w in cfg.STOPWORDS or w in cfg.FIBER_MODIFIERS or w in cfg.PART_ALIASES:
        return None
    return w, "unknown", a, b


# ---------------------------------------------------------------- cleaning

def _prepare(raw: str, flags: dict) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = text.replace("\xa0", " ").replace("*", "").replace("`", "")
    text = re.sub(r"[ \t]+", " ", text)
    if _MAY_CONTAIN_RE.search(text):
        flags["may_contain"] = True
        text = _MAY_CONTAIN_RE.sub(" ", text)
    if _APPROX_RE.search(text):
        flags["approx"] = True
        text = _APPROX_RE.sub(" ", text)
    return text


def _hoist_parenthetical_labels(text: str) -> str:
    """'100% cotton (shell), 100% polyester (lining)' -> 'shell: 100% cotton' / 'lining: ...'."""
    out, rest = [], text
    while True:
        m = _PAREN_LABEL_RE.search(rest)
        if not m or not _PCT_RE.search(rest[: m.start()]):
            break
        out.append(f"\n{m.group('label')}: {rest[: m.start()].strip(' ,;')}\n")
        rest = rest[m.end():].lstrip(" ,;")
    out.append(rest)
    return "".join(out)


def _split_labels(piece: str) -> list[_Seg]:
    """Cut a piece of text at label words; each chunk belongs to the label that precedes it."""
    segs: list[_Seg] = []
    last_end, last_part = 0, None
    for m in _LABEL_RE.finditer(piece):
        segs.append(_Seg(last_part, piece[last_end:m.start()]))
        last_part = cfg.PART_ALIASES[m.group("label").lower()]
        last_end = m.end()
    segs.append(_Seg(last_part, piece[last_end:]))
    return [s for s in segs if s.part is not None or s.text.strip()]


# ---------------------------------------------------------------- pair extraction

def _fiber_first(text: str, first) -> bool:
    gap = text[: first.start()].rstrip(" :-–=\t")
    cut = max((gap.rfind(d) for d in _DELIMS), default=-1)
    ws = _words(gap[cut + 1:])
    return any(_lookup([w[0] for w in ws[-n:]]) for n in range(1, min(3, len(ws)) + 1))


def _extract_pairs(text: str, flags: dict, notes: list[str]) -> list[FiberShare]:
    toks = list(_PCT_RE.finditer(text))
    if not toks:
        return []
    fiber_first = _fiber_first(text, toks[0])
    pairs: list[FiberShare] = []
    for i, tok in enumerate(toks):
        if tok.group("hi"):
            flags["range"] = flags["dropped"] = True
            notes.append(f"range not parsed: '{tok.group().strip()}'")
            continue
        value = float(tok.group("lo").replace(",", "."))
        if value > 100:
            flags["dropped"] = True
            notes.append(f"percentage over 100 ignored: '{tok.group().strip()}'")
            continue
        if fiber_first:
            start = toks[i - 1].end() if i else 0
            gap = text[start:tok.start()].rstrip(" :-–=\t")
            cut = max((gap.rfind(d) for d in _DELIMS), default=-1)
            ws = _words(gap[cut + 1:], start + cut + 1)
            res = _resolve_backward(ws) if ws else None
        else:
            end = toks[i + 1].start() if i + 1 < len(toks) else len(text)
            run = text[tok.end():end]
            cuts = [run.find(d) for d in _DELIMS if run.find(d) >= 0]
            if cuts:
                run = run[: min(cuts)]
            ws = _words(run, tok.end())
            res = _resolve_forward(ws) if ws else None
        if res is None:
            flags["dropped"] = True
            notes.append(f"no fiber name next to '{tok.group().strip()}'")
            continue
        canon, category, a, b = res
        lo = min(tok.start(), a)
        hi = max(tok.end(), b)
        pairs.append(FiberShare(fiber=canon, percent=value, category=category,
                                original=text[lo:hi].strip(" ,:;-–")))
    return pairs


# ---------------------------------------------------------------- assembling parts

def _signature(c: Component):
    return sorted((f.fiber, f.percent) for f in c.fibers)


def _is_translation_of(c: Component, kept: Component) -> bool:
    if _signature(c) == _signature(kept):
        return True
    if all(f.category == "unknown" for f in c.fibers):
        return sorted(f.percent for f in c.fibers) == sorted(f.percent for f in kept.fibers)
    return False


def _assemble(segments: list[_Seg]) -> list[Component]:
    comps: list[Component] = []
    open_group: Component | None = None
    for seg in segments:
        if not seg.pairs:
            continue
        if seg.part is not None:
            open_group = None
            comps.append(Component(part=seg.part, fibers=list(seg.pairs)))
            continue
        for pair in seg.pairs:
            if open_group is None or open_group.total_percent >= 99.99:
                open_group = Component(part="unspecified", fibers=[])
                comps.append(open_group)
            open_group.fibers.append(pair)
    kept: list[Component] = []
    for c in comps:
        if any(k.part == c.part and _is_translation_of(c, k) for k in kept):
            continue
        kept.append(c)
    return kept


def _choose_main(comps: list[Component], notes: list[str]) -> Component | None:
    shells = [c for c in comps if c.part == "shell"]
    if len(shells) == 1:
        return shells[0]
    if len(shells) > 1:
        notes.append("several different shell/body compositions; main fabric unclear")
        return None
    unspecified = [c for c in comps if c.part == "unspecified"]
    if len(unspecified) == 1:
        return unspecified[0]
    if len(unspecified) > 1:
        notes.append("several unlabelled compositions; main fabric unclear")
        return None
    notes.append("only lining/trim/filling/sleeve compositions given; no main fabric identified")
    return None


def _sum(comp: Component, cats) -> float:
    return round(sum(f.percent for f in comp.fibers if f.category in cats), 2)


# ---------------------------------------------------------------- public API

def parse_composition(raw: str | None, *, count_regenerated_as_natural: bool | None = None) -> ParsedComposition:
    """Parse composition text into parts and fibers, and compute natural_fiber_pct for the main part."""
    if count_regenerated_as_natural is None:
        count_regenerated_as_natural = cfg.COUNT_REGENERATED_AS_NATURAL
    res = ParsedComposition()
    if raw is None or not raw.strip():
        res.notes.append("no composition text")
        return res

    flags: dict = {}
    text = _hoist_parenthetical_labels(_prepare(raw, flags))

    segments: list[_Seg] = []
    pending: str | None = None
    for piece in _SENTENCE_SPLIT_RE.split(text):
        if not piece or not piece.strip():
            continue
        segs = _split_labels(piece)
        for s in segs:
            s.pairs = _extract_pairs(s.text, flags, res.notes)
        out: list[_Seg] = []
        for idx, s in enumerate(segs):
            if s.part is not None and not s.pairs and not s.text.strip(" ,.:-–"):
                prev = out[-1] if out else None
                if prev is not None and prev.part is None and prev.pairs:
                    prev.part = s.part        # trailing label: "100% cotton body"
                else:
                    pending = s.part          # label on its own line, pairs on the next
                continue
            if s.part is None and s.pairs and pending is not None:
                s.part, pending = pending, None
            elif s.part is not None and s.pairs:
                pending = None
            out.append(s)
        segments.extend(out)

    comps = _assemble(segments)
    if flags.get("may_contain"):
        res.notes.append("'may contain' text ignored")
    res.components = comps

    if not comps:
        mentioned = any(_lookup([w[0]]) for w in _words(text))
        res.confidence = "ambiguous" if mentioned else "missing"
        res.notes.append("fibers mentioned without percentages" if mentioned
                         else "no fiber percentages found")
        return res

    main = _choose_main(comps, res.notes)
    ambiguous = main is None
    if flags.get("approx"):
        res.notes.append("approximate figures ('approx.')")
        ambiguous = True
    if flags.get("range"):
        ambiguous = True
    if main is not None:
        total = main.total_percent
        res.main_part = main.part
        res.regenerated_fiber_pct = _sum(main, {"regenerated"})
        res.synthetic_fiber_pct = _sum(main, {"synthetic"})
        res.unknown_fiber_pct = _sum(main, {"unknown"})
        if total > 100 + cfg.SUM_TOLERANCE:
            res.notes.append(f"percentages total {total}, over 100; natural share not reported")
            ambiguous = True
        elif flags.get("dropped"):
            res.notes.append("part of the composition could not be read; natural share not reported")
            ambiguous = True
        else:
            cats = NATURAL_CATEGORIES | ({"regenerated"} if count_regenerated_as_natural else set())
            res.natural_fiber_pct = _sum(main, cats)
            if total < 100 - cfg.SUM_TOLERANCE:
                res.notes.append(f"percentages total {total}, under 100; not rescaled")
                ambiguous = True
        if res.unknown_fiber_pct:
            res.notes.append(f"{res.unknown_fiber_pct}% is an unrecognised fiber")
            ambiguous = True
    res.confidence = "ambiguous" if ambiguous else "explicit"
    return res


# ---------------------------------------------------------------- finding composition in page markdown

_LABEL_ONLY_RE = re.compile(rf"^\W*(?:{_LABEL_ALTS})\W*$", re.IGNORECASE)


def _line_has_composition(line: str) -> bool:
    if not _PCT_RE.search(line):
        return False
    return any(_lookup([w[0]]) for w in _words(line))


def find_composition_text(markdown: str | None) -> tuple[str | None, int]:
    """Fallback when the extractor returned no composition: scan the page markdown for fiber lines.

    Returns (text of the first block found, number of distinct blocks). More than one distinct
    block (e.g. a "related products" carousel) means the caller should treat it as ambiguous.
    """
    if not markdown:
        return None, 0
    blocks: list[list[str]] = []
    cur: list[str] = []
    blank_run = 0
    for line in markdown.splitlines():
        s = line.strip()
        if not s:
            blank_run += 1
            if blank_run >= 2 and cur:
                blocks.append(cur)
                cur = []
            continue
        blank_run = 0
        if _line_has_composition(s) or _LABEL_ONLY_RE.match(s):
            cur.append(s)
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    cleaned: list[str] = []
    for b in blocks:
        while b and not _line_has_composition(b[-1]):
            b = b[:-1]
        while b and _LABEL_ONLY_RE.match(b[0]) and not any(_line_has_composition(x) for x in b[1:2]):
            b = b[1:]
        if any(_line_has_composition(x) for x in b):
            cleaned.append("\n".join(b))
    distinct = list(dict.fromkeys(cleaned))
    return (distinct[0] if distinct else None), len(distinct)
