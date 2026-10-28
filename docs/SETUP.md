# Developer setup

How to get QuickShop running on your machine and where to put your code.

## What you need

- Python 3.10 or newer (3.12 is what we tested with)
- An ASU key from the Voyager portal for the model gateway

## Setup

1. Make a virtual environment and turn it on:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows use `.venv\Scripts\activate` instead.

2. Install the project and the test tool:

```bash
pip install -e ".[dev]"
```

3. Make your own `.env` file and put your key in it:

```bash
cp .env.example .env
```

Then open `.env` and fill in the value, like `API_KEY=your_key_here`.
Write it as `NAME=value` with no quotes and no spaces. Never commit `.env`. It is already ignored by git.

## What goes in .env

| Name | What it is | When you need it |
|------|------------|------------------|
| API_KEY | ASU gateway key from the Voyager portal | Now |

When you add a new key (for example for SerpAPI or Firecrawl), read it in your code with `os.getenv("NAME")`, add an empty `NAME=` line to `.env.example`, and tell the team to add their own value.

## Check it works

```bash
pytest
python -m quickshop "black straight jeans under 80 dollars"
```

`pytest` runs without a key. The second command talks to the model, so it needs `API_KEY`.
The tools are fake for now, so no search or scraping keys are needed yet.

## Where things are

```
quickshop/
  config.py          model setup (ASU gateway)
  schemas.py         the shapes of the data the tools return
  agent/
    orchestrator.py  builds the agent, the only file that calls the harness
    prompts.py       the instructions the agent follows
    interventions.py limit on expensive page reads
    hooks.py         writes down every tool call
  tools/
    stubs.py         fake versions of four tools
    user.py          ask_user, asks the shopper a question
    __init__.py      the list of tools the agent gets
  fixtures/          fake data used by the stubs
tests/               tests that run without the internet
```

## Adding a real tool

1. Write your tool in a new file in `quickshop/tools/`, with the `@tool` decorator.
2. Keep the same name, arguments and return shape as the fake one in `stubs.py`. Keep the docstring too, because the model reads it to know when to use the tool.
3. In `quickshop/tools/__init__.py`, import your tool instead of the fake one.
4. If you need a key or a package, add them to `.env.example` and `pyproject.toml`.
5. Run `pytest`.

Rules for every tool:

- Return the shape from `schemas.py`.
- If you cannot find something, leave it as `None` or set `available` to false. Do not guess a value.
- Cheap tools (search, merchant check) can be called many times. Page reading is expensive and the agent can only do a few per request.

## Good to know

- Sessions are not saved to disk unless you pass a `session_id`, because a shopper's size and height should not be stored.
- The harness version is pinned in `pyproject.toml`. Change it on purpose, not by accident.
