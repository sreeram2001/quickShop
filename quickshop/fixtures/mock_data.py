# Dummy data so the agent can run before the real tools exist.
LISTINGS = [
    {
        "title": "Levi's 501 Straight Jeans - Black",
        "price": 69.99,
        "merchant": "Levi's",
        "domain": "levi.com",
        "rating": 4.6,
        "reviews": 5200,
        "url": "https://example.com/levis-501",
    },
    {
        "title": "Uniqlo Regular Fit Straight Jeans",
        "price": 49.90,
        "merchant": "Uniqlo",
        "domain": "uniqlo.com",
        "rating": 4.3,
        "reviews": 3400,
        "url": "https://example.com/uniqlo-straight",
    },
    {
        "title": "Classic Straight-Leg Denim - Black",
        "price": 24.99,
        "merchant": "StyleMarket247",
        "domain": "stylemarket247.shop",
        "rating": 4.9,
        "reviews": 12,
        "url": "https://example.com/stylemarket",
    },
]

EVIDENCE = {
    "https://example.com/levis-501": {
        "composition": {"cotton": 100},
        "origin": "Mexico",
        "seller_identity": "Levi Strauss & Co",
        "return_policy": True,
        "color": "black",
    },
    "https://example.com/uniqlo-straight": {
        "composition": {"cotton": 98, "elastane": 2},
        "origin": "Vietnam",
        "seller_identity": "Uniqlo USA",
        "return_policy": True,
        "color": "black",
    },
    "https://example.com/stylemarket": {
        "composition": None,
        "origin": None,
        "seller_identity": None,
        "return_policy": False,
        "color": "black",
    },
}

MERCHANTS = {
    "Levi's": {
        "known_brand": True,
        "domain_age_years": 28,
        "third_party_reviews": 45000,
        "return_policy": True,
    },
    "Uniqlo": {
        "known_brand": True,
        "domain_age_years": 20,
        "third_party_reviews": 30000,
        "return_policy": True,
    },
    "StyleMarket247": {
        "known_brand": False,
        "domain_age_years": 0.4,
        "third_party_reviews": 12,
        "return_policy": False,
    },
}

# Fixed scores for now. The real scoring will be plain Python over the evidence.
SCORES = {
    "https://example.com/levis-501": {
        "price": 4,
        "quality": 5,
        "legitimacy": 5,
        "overall": 4.7,
        "eligible": True,
        "risk": "low",
        "evidence": ["100% cotton", "known brand, 45000 reviews, return policy"],
    },
    "https://example.com/uniqlo-straight": {
        "price": 5,
        "quality": 5,
        "legitimacy": 5,
        "overall": 5.0,
        "eligible": True,
        "risk": "low",
        "evidence": ["98% cotton", "known brand, 30000 reviews, return policy"],
    },
    "https://example.com/stylemarket": {
        "price": 2,
        "quality": 1,
        "legitimacy": 1,
        "overall": 1.2,
        "eligible": False,
        "risk": "high",
        "evidence": ["fabric not disclosed", "site under 1 year old, 12 reviews, no return policy"],
    },
}
