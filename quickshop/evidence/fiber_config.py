# All fiber knowledge lives here, as data. The parser (fabric.py) has no fiber names in its code.

# DECISION FLAG: does regenerated cellulose (viscose, modal, lyocell...) count as "natural fiber"?
# Default is no. It is always reported separately as regenerated_fiber_pct either way.
COUNT_REGENERATED_AS_NATURAL = False

# A composition whose percentages do not total 100 +/- this is marked ambiguous (never rescaled).
SUM_TOLERANCE = 1.0

# canonical fiber -> category
FIBER_CATEGORY: dict[str, str] = {
    # natural plant
    "cotton": "natural_plant", "linen": "natural_plant", "hemp": "natural_plant",
    "jute": "natural_plant", "ramie": "natural_plant",
    # natural animal
    "wool": "natural_animal", "cashmere": "natural_animal", "silk": "natural_animal",
    "alpaca": "natural_animal", "mohair": "natural_animal", "angora": "natural_animal",
    "camel": "natural_animal", "yak": "natural_animal", "llama": "natural_animal",
    # regenerated cellulose
    "viscose": "regenerated", "modal": "regenerated", "lyocell": "regenerated",
    "cupro": "regenerated", "acetate": "regenerated", "triacetate": "regenerated",
    "bamboo": "regenerated",
    # synthetic
    "polyester": "synthetic", "nylon": "synthetic", "acrylic": "synthetic",
    "elastane": "synthetic", "polypropylene": "synthetic", "polyurethane": "synthetic",
    "modacrylic": "synthetic", "polyethylene": "synthetic", "aramid": "synthetic",
    # unknown bucket
    "other_fibers": "unknown",
}

# alias (lowercase) -> canonical fiber. Includes a few French/German/Spanish/Italian names.
_ALIASES_BY_FIBER: dict[str, list[str]] = {
    "cotton": ["cotton", "coton", "baumwolle", "algodon", "algodón", "cotone", "katoen"],
    "linen": ["linen", "flax", "lin", "leinen", "lino"],
    "hemp": ["hemp", "hanf", "chanvre", "cáñamo", "canamo"],
    "jute": ["jute"], "ramie": ["ramie"],
    "wool": ["wool", "lambswool", "lamb's wool", "merino", "new wool", "wolle", "laine", "lana"],
    "cashmere": ["cashmere", "kaschmir", "cachemire", "cachemira", "cashmir"],
    "silk": ["silk", "seide", "soie", "seda", "seta"],
    "alpaca": ["alpaca"], "mohair": ["mohair"], "angora": ["angora"],
    "camel": ["camel", "camel hair"], "yak": ["yak"], "llama": ["llama"],
    "viscose": ["viscose", "rayon", "viskose", "viscosa"],
    "modal": ["modal", "tencel modal"],
    "lyocell": ["lyocell", "tencel", "tencel lyocell"],
    "cupro": ["cupro"], "acetate": ["acetate", "acetat"], "triacetate": ["triacetate"],
    "bamboo": ["bamboo"],
    "polyester": ["polyester", "poly", "poliester", "poliéster", "poliestere"],
    "nylon": ["nylon", "polyamide", "polyamid", "polyamida", "poliammide"],
    "acrylic": ["acrylic", "acryl", "acrylique", "acrílico", "acrilico"],
    "elastane": ["elastane", "spandex", "lycra", "elasthane", "elasthanne", "élasthanne",
                 "elasthan", "elastan", "elastano", "elastán"],
    "polypropylene": ["polypropylene", "polypropylen"],
    "polyurethane": ["polyurethane", "polyurethan", "pu"],
    "modacrylic": ["modacrylic"], "polyethylene": ["polyethylene"], "aramid": ["aramid"],
    "other_fibers": ["other fibres", "other fibers", "other fibre", "other fiber",
                     "other materials", "other material", "others", "other"],
}
FIBER_ALIASES: dict[str, str] = {
    alias: fiber for fiber, aliases in _ALIASES_BY_FIBER.items() for alias in aliases
}

# Words that describe a fiber but do not change what it is: "organic cotton" -> cotton.
FIBER_MODIFIERS: set[str] = {
    "organic", "pure", "recycled", "virgin", "supima", "pima", "egyptian", "premium", "combed",
    "brushed", "mulberry", "lenzing", "soft", "fine", "extra", "genuine", "real", "natural",
    "stretch", "ring-spun", "worsted", "regenerated",
}

# label word in the text -> part of the garment
PART_ALIASES: dict[str, str] = {
    "shell": "shell", "outer shell": "shell", "shell fabric": "shell", "outer fabric": "shell",
    "main fabric": "shell", "main material": "shell", "body fabric": "shell", "body": "shell",
    "exterior": "shell", "outer": "shell", "obermaterial": "shell", "oberstoff": "shell",
    "außenmaterial": "shell", "aussenmaterial": "shell", "extérieur": "shell",
    "lining": "lining", "lined": "lining", "interior": "lining", "inner": "lining",
    "futter": "lining", "doublure": "lining", "forro": "lining", "fodera": "lining",
    "trim": "trim", "contrast": "trim", "ribbing": "trim", "rib": "trim", "pocketing": "trim",
    "pocket": "trim", "collar": "trim", "cuff": "trim", "cuffs": "trim",
    "filling": "filling", "fill": "filling", "padding": "filling", "insulation": "filling",
    "sleeve": "sleeve", "sleeves": "sleeve",
}

# Words that are never a fiber name (care text, filler). Used so "100% cotton machine wash" is safe.
STOPWORDS: set[str] = {
    "and", "or", "with", "the", "of", "a", "an", "in", "on", "at", "machine", "wash", "washable",
    "hand", "dry", "clean", "cleaning", "do", "not", "bleach", "tumble", "iron", "ironing", "cold",
    "warm", "hot", "cool", "only", "care", "fabric", "material", "materials", "fibre", "fibres",
    "fiber", "fibers", "content", "composition", "made", "imported", "import", "lined", "unlined",
    "fully", "partially", "total", "approx", "about", "may", "contain", "contains", "natural",
    "blend", "blended", "mix", "mixed", "per", "cent", "percent", "product", "item", "garment",
    "size", "fit", "model", "is", "are", "as", "by", "from", "for", "to", "this", "that", "it",
    "its", "has", "have", "comes", "label", "imported", "recommend", "recommended", "satisfaction",
    "polyester-free", "free",
}
