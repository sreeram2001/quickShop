# To run use: python -m quickshop "black jeans under $80"
import sys

from quickshop.agent.orchestrator import build_agent

def main():
    agent = build_agent()
    request = " ".join(sys.argv[1:]) or input("What are you looking for? ").strip()
    # the agent keeps the chat in memory, so follow-ups can work
    while request:
        agent(request)
        print()
        request = input("Anything else? (press Enter to quit) ").strip()
    print(f"Tool calls this run: {len(agent.trace.calls)}")

if __name__ == "__main__":
    main()
