"""Minimal interactive interface: run with `python3 -m src.cli`."""
import os

from src.assistant import investigate


def main():
    print("SupplyChain Copilot demo (type 'exit' to quit)")
    print("Example: Shipment S-104 is delayed. Which orders are at risk?")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        use_openai = os.getenv("OPENAI_API_KEY") and os.getenv("SUPPLYCHAIN_OFFLINE") != "1"
        if use_openai:
            try:
                from src.openai_agent import answer_with_openai
                print("\nAssistant: " + answer_with_openai(
                    question, model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                ))
                continue
            except ImportError:
                print("OpenAI SDK missing. Install dependencies with: python3 -m pip install -r requirements.txt")
                continue
            except Exception as exc:
                try:
                    from openai import APIError
                except ImportError:
                    APIError = ()
                if not isinstance(exc, APIError):
                    raise
                print(f"\nOpenAI API unavailable ({type(exc).__name__}); showing offline result instead.")

        answer = investigate(question)
        if answer["at_risk_orders"]:
            print("\nPotential order shortfalls:")
            for order in answer["at_risk_orders"]:
                print(
                    f"- {order['order_id']}: {order['qty_uncovered']} of "
                    f"{order['qty_needed']} units uncovered; due {order['due_date']} "
                    f"(shipment {order['shipment_id']} expected {order['expected_arrival_date']})"
                )
        elif not answer["warnings"]:
            print("\nNo at-risk orders found in the demo records.")
        for warning in answer["warnings"]:
            print(f"\nNote: {warning}")
        if answer["references"]:
            print("\nRetrieved reference passages (general import context, not shipment evidence):")
            for ref in answer["references"]:
                print(f"- {ref['title']} — {ref['url']}")
                print(f"  {ref['text'][:240]}...")
        print(f"\nRead-only tool calls: {answer['tool_calls']}/{2}")


if __name__ == "__main__":
    main()
