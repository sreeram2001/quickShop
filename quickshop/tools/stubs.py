# Fake versions of four tools. Teammates replace these with the real ones.
# Keep the tool names, the arguments and the return shapes the same.
from strands import tool

from quickshop.fixtures.mock_data import EVIDENCE, LISTINGS, MERCHANTS, SCORES
from quickshop.schemas import Evidence, Listing, MerchantSignals, Scores

@tool
def search_listings(query: str) -> list:
    """Search online stores for clothing listings. This is cheap, so it can be repeated.

    Args:
        query: What to search for, for example "black straight jeans".

    Returns:
        A list of listings with title, price, merchant, domain, rating, reviews and url.
    """
    return [Listing(**item).model_dump() for item in LISTINGS]

@tool
def fetch_product_evidence(url: str) -> dict:
    """Read a product page for fabric, origin and seller details.
    This is expensive, each call uses one page-reading credit.

    Args:
        url: The product page url from a listing.

    Returns:
        The evidence record. available is false if the page could not be read.
    """
    if url not in EVIDENCE:
        return Evidence(url=url, available=False).model_dump()
    return Evidence(url=url, **EVIDENCE[url]).model_dump()

@tool
def check_merchant(merchant: str) -> dict:
    """Check how trustworthy a seller is. This is cheap, so use it before reading pages.

    Args:
        merchant: The seller name from a listing, for example "Levi's".

    Returns:
        Seller signals. available is false if nothing is known about the seller.
    """
    if merchant not in MERCHANTS:
        return MerchantSignals(merchant=merchant, available=False).model_dump()
    return MerchantSignals(merchant=merchant, **MERCHANTS[merchant]).model_dump()

@tool
def score_product(url: str) -> dict:
    """Score a product from 1 to 5 on price, quality and legitimacy.
    If eligible is false the seller is not trusted and the item must not be recommended.

    Args:
        url: The product page url from a listing.

    Returns:
        The scores, eligible, risk (low, medium, high) and the evidence behind them.
        available is false if there is not enough evidence.
    """
    if url not in SCORES:
        return Scores(url=url, available=False).model_dump()
    return Scores(url=url, **SCORES[url]).model_dump()
