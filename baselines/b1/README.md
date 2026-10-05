# B1 : Web-connected, non-agentic baseline

A fixed pipeline that has the **same data access** as the full QuickShop agent but **none of its
agency**. Comparing against B1 isolates the contribution of adaptive search, selective extraction,
and the scoring rule, separating it from the contribution of simply being online.

## Pipeline 
1. **One** SerpAPI Google Shopping search for the raw query : no clarification, no re-search.
2. Take the **top 10** listings as-is : no triage, no selective deep extraction.
3. **One** LLM call scoring all 10 from **listing metadata only** : no product-page evidence.
4. **Arithmetic average** of the three axes (the same aggregation defect as B0).
5. Return the **top 3**. No recovery, no abstain.

## Run

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python3 run.py
```

- The input query is read from `input.txt`.
- Output is written to `output.txt` and printed.