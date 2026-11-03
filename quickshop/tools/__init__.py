from quickshop.evidence.tool import fetch_product_evidence
from quickshop.tools.stubs import check_merchant, score_product, search_listings
from quickshop.tools.user import ask_user

# The agent gets these five tools and nothing else.
# fetch_product_evidence is real (Firecrawl). The others are still stubs: swap them in as they are finished.
DEFAULT_TOOLS = [search_listings, check_merchant, fetch_product_evidence, score_product, ask_user]
