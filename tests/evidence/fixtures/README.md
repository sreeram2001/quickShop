# Evidence test fixtures

Each `*.json` file is a saved Firecrawl response shape: `markdown`, `json` (the schema-constrained
extraction) and `metadata` (`status_code`, `credits_used`). Tests replay them through a fake scraper,
so no network or API key is needed.

## Real captures (`live_*.json`)

Saved from the live Firecrawl API on 2026-11-02, one scrape each (5 credits):

| File | Page | Why it is here |
|------|------|----------------|
| `live_jacket_shell_lining.json` | Levi's Washed Cotton Field Jacket (altitude-sports.com) | Shell 100% cotton + Lining 100% polyester: the main fabric must be the shell |
| `live_tee_cotton_poly_blend.json` | Hooey Desert Dillo tee (academy.com) | 50% cotton / 50% polyester blend written as a sentence |

## Synthetic fixtures (everything else)

Written by hand to mimic real page structure (bullet list, table, missing composition, blocked page,
non-product page, extractor miss, invented composition). Retailer names use placeholder `example.test`
domains. No real missing-composition or blocked page has been captured yet: every real page tried so
far was readable. Replace these when a real one turns up.
