# It asks the shopper a question in the terminal.
from strands import tool

@tool
def ask_user(question: str) -> str:
    """Ask the shopper a short question, for example their size or height.
    Ask one question at a time and only for what you need.

    Args:
        question: The question to show the shopper.

    Returns:
        The shopper's answer, or a note that there was no answer.
    """
    try:
        answer = input(f"\nQuickShop asks: {question}\n> ").strip()
    except EOFError:
        answer = ""
    return answer or "No answer given. Continue without it and say so in your reply."
