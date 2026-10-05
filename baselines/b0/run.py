import argparse
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def load_products(filename):
    with open(filename, "r") as file:
        return json.load(file)


def load_request(filename):
    with open(filename, "r") as file:
        return file.read().strip()


def build_prompt(user_request, products):
    product_text = json.dumps(products, indent=2)

    return f"""
You are a shopping recommendation system.

Your task is to recommend clothing products based ONLY on the information
provided below. Do not assume information that is not included.

Evaluate products using three categories:

1. PRICE
- The product should satisfy the user's stated budget.
- Do not recommend products above the maximum budget.

2. QUALITY
- Consider the provided material composition.
- Consider the product rating and number of reviews.
- Missing information should be treated as uncertainty.
- Do not assume that a specific material automatically guarantees quality.

3. LEGITIMACY
- Consider the provided information about the seller.
- Do not claim that a seller is definitely legitimate or a scam.
- Limited seller information should be treated as uncertainty.

Give each product a score from 1 to 5 for:
- Price
- Quality
- Legitimacy

Then recommend the three products that best match the user's request.

For each recommendation, provide:
- Product name
- Price
- Price score
- Quality score
- Legitimacy score
- Overall score
- A short explanation

Also identify products that were rejected and explain why.

USER REQUEST:
{user_request}

PRODUCTS:
{product_text}
"""


def call_llm(prompt, mock=False):
    if mock:
        return (
            "[MOCK OUTPUT] No API call was made.\n"
            "This is where gpt-oss-120b would return per-axis scores (price, quality,\n"
            "legitimacy), an overall score averaged across the three axes, around three\n"
            "recommendations, and the reasons the remaining products were rejected.\n"
        )

    client = OpenAI(
        base_url="https://openai.rc.asu.edu/v1",
        api_key=os.getenv("API_KEY"),
    )
    response = client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(description="QuickShop B0 baseline")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without calling the API (uses a placeholder response).",
    )
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    products = load_products(os.path.join(here, "products.json"))
    user_request = load_request(os.path.join(here, "input.txt"))

    prompt = build_prompt(user_request, products)
    result = call_llm(prompt, mock=args.mock)

    out_path = os.path.join(here, "output.txt")
    with open(out_path, "w") as file:
        file.write(result)

    print(f"result written in {out_path}")


if __name__ == "__main__":
    main()
