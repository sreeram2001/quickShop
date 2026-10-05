# Baselines
| **B0** | Stakeholder's original single LLM call over a hand-filled `products.json`.
| **B1** | Fixed, non-agentic pipeline: one SerpAPI search → one LLM scoring call over listing metadata.
| **B2** | Single web-grounded LLM call (model's native web search)

**Why three.** With only B0, an improvement could be explained by the agent simply being online.
B1 has the *same data access* as the full agent but none of its agency, which isolates the
contribution of adaptive search, selective extraction, and the scoring rule. B2 checks whether a
plain web-grounded model is already "good enough," which the project should learn early.

## Run
```bash
python3 run.py
```
