# B0 : Original baseline (unchanged)

stakeholder's original baseline:
<https://github.com/sarahmaisha/cse598quickshop>

## What it does

1. Reads a request from `input.txt`.
2. Reads five hand-filled products from `products.json`.
3. Makes **one** `gpt-oss-120b` call (ASU RC gateway) that scores each product 1–5 on price,
   quality, and legitimacy, and recommends about three.
4. Writes the result to `output.txt`.

## Aggregation

The Python code does **not** compute an average : aggregation is delegated to the LLM inside the
prompt. However, the stakeholder's own `output_example.txt` states the overall score as
`(Price + Quality + Legitimacy) ÷ 3`. So the *arithmetic-mean behavior* is real and visible in the
baseline's output, even though it is not a deterministic step in the code. The known defect
follows directly: a product scoring high on price and quality but low on legitimacy still averages
well enough to be recommended. QuickShop replaces this with a legitimacy gate plus a weighted
geometric mean.

## Run

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python3 run.py
```
