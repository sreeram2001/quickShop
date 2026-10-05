import argparse
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TOP_N = 10
RECOMMEND_N = 3


def read_query(path):
    with open(path, "r") as f:
        return f.read().strip()


def search_listings(query, mock=False):
    if mock:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "fixtures", "serpapi_response.json")) as f:
            data = json.load(f)
    else:
        import requests

        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": os.getenv("SERPAPI_KEY"),
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("shopping_results", [])[:TOP_N]
    listings = []
    for r in results:
        listings.append(
            {
                "title": r.get("title"),
                "price": r.get("extracted_price", r.get("price")),
                "merchant": r.get("source"),
                "rating": r.get("rating"),
                "reviews": r.get("reviews"),
                "link": r.get("link") or r.get("product_link"),
            }
        )
    return listings


def build_prompt(query, listings):
    listing_text = json.dumps(listings, indent=2)
    return f"""
You are a shopping recommendation system. Score each listing ONLY from the
metadata provided (title, price, merchant, rating, reviews). You do NOT have the
product page, so treat missing material/seller detail as uncertainty.

For EACH listing give integer scores 1-5 for:
- price   (fit to the user's budget if stated; cheaper-but-reasonable scores higher)
- quality (infer cautiously from title + rating + review count)
- legitimacy (infer cautiously from merchant name + review volume)

Return STRICT JSON: a list of objects with keys
  title, price, price_score, quality_score, legitimacy_score, reason

USER REQUEST:
{query}

LISTINGS:
{listing_text}
"""


def score_with_llm(query, listings, mock=False):
    if mock:
        scored = []
        for ls in listings:
            rating = ls.get("rating") or 0
            reviews = ls.get("reviews") or 0
            quality = 5 if rating >= 4.5 and reviews >= 500 else 3 if rating else 2
            legit = 5 if reviews >= 1000 else 3 if reviews >= 100 else 2
            price = 5 if (ls.get("price") or 999) <= 80 else 1
            scored.append(
                {
                    "title": ls["title"],
                    "price": ls.get("price"),
                    "price_score": price,
                    "quality_score": quality,
                    "legitimacy_score": legit,
                    "reason": "[MOCK] scored from fixture metadata only",
                }
            )
        return scored

    client = OpenAI(
        base_url="https://openai.rc.asu.edu/v1", api_key=os.getenv("API_KEY")
    )
    resp = client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[{"role": "user", "content": build_prompt(query, listings)}],
    )
    content = resp.choices[0].message.content
    try:
        start, end = content.index("["), content.rindex("]") + 1
        return json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError):
        return [{"raw_model_output": content}]


def rank(scored):
    ranked = []
    for s in scored:
        if "price_score" not in s:
            continue
        overall = (s["price_score"] + s["quality_score"] + s["legitimacy_score"]) / 3
        ranked.append({**s, "overall": round(overall, 2)})
    ranked.sort(key=lambda x: x["overall"], reverse=True)
    return ranked


def render(query, ranked):
    lines = [f"B1 baseline — query: {query}", "=" * 60, ""]
    lines.append(f"Top {RECOMMEND_N} recommendations (arithmetic average of 3 axes):\n")
    for i, r in enumerate(ranked[:RECOMMEND_N], 1):
        lines.append(
            f"{i}. {r['title']}  (${r.get('price')})\n"
            f"   price={r['price_score']} quality={r['quality_score']} "
            f"legitimacy={r['legitimacy_score']}  overall={r['overall']}\n"
            f"   {r.get('reason', '')}\n"
        )
    if len(ranked) > RECOMMEND_N:
        lines.append("Not recommended:")
        for r in ranked[RECOMMEND_N:]:
            lines.append(f"   - {r['title']} (overall={r['overall']})")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="QuickShop B1 baseline")
    parser.add_argument(
        "--mock", action="store_true", help="Run offline with fixtures, no keys."
    )
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    query = read_query(os.path.join(here, "input.txt"))

    listings = search_listings(query, mock=args.mock)
    scored = score_with_llm(query, listings, mock=args.mock)
    ranked = rank(scored)
    output = render(query, ranked)

    out_path = os.path.join(here, "output.txt")
    with open(out_path, "w") as f:
        f.write(output)
    print(output)
    print(f"\nresult written in {out_path}")


if __name__ == "__main__":
    main()
