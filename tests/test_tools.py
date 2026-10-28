from quickshop.tools.stubs import check_merchant, fetch_product_evidence, score_product, search_listings

def test_search_returns_listings():
    listings = search_listings("black jeans")
    assert len(listings) > 0
    assert "price" in listings[0]

def test_unknown_page_is_unavailable_not_guessed():
    result = fetch_product_evidence("https://nowhere.example")
    assert result["available"] is False
    assert result["composition"] is None

def test_unknown_merchant_is_unavailable():
    assert check_merchant("Nobody Inc")["available"] is False

def test_bad_seller_is_not_eligible():
    scores = score_product("https://example.com/stylemarket")
    assert scores["eligible"] is False
    assert scores["risk"] == "high"
