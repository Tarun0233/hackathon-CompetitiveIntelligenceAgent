import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY"),
)

queries = [
    (
        "TEST A — KNOWN PRECEDENT",
        "MetroKart launched a 20% weekend discount. What should Dhan Mart do in response?",
    ),
    (
        "TEST B — RELATED BUT DIFFERENT",
        "A competitor has introduced a price-matching program. How should Dhan Mart respond?",
    ),
    (
    "TEST C — GENUINELY NEW SITUATION",
    "A competitor has suddenly introduced free same-day returns for grocery orders above ₹2,000. What should Dhan Mart investigate before deciding how to respond?",
    ),
]

for test_name, query in queries:

    print("\n")
    print("=" * 90)
    print(test_name)
    print("=" * 90)

    print("\nQUERY:")
    print(query)

    response = client.recall(
        bank_id="competitive-intel-demo-live",
        query=query,
        trace=True,
        budget="mid",
    )

    print("\nTOP 5 RESULTS")
    print("=" * 90)

    for i, result in enumerate(response.results[:5], 1):

        print(f"\nRESULT {i}")
        print("-" * 70)

        print("TEXT:")
        print(result.text)

        print("\nTYPE:")
        print(result.type)

        print("\nSCORES:")
        print(result.scores)

    print("\n\nTRACE")
    print("=" * 90)
    print(response.trace)


client.close()