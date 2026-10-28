from quickshop.tools.stubs import check_merchant, fetch_product_evidence, score_product, search_listings
from quickshop.tools.user import ask_user

# The agent gets these five tools and nothing else.
# When a teammate finishes a real tool, import it here instead of the stub.
DEFAULT_TOOLS = [search_listings, check_merchant, fetch_product_evidence, score_product, ask_user]
