import os
import sys
from dotenv import load_dotenv
from hindsight_client import Hindsight

from synthetic_data import (
    STAGES,
    memories_until,
    to_retain_kwargs,
)


load_dotenv()


def main(stage: str) -> None:
    valid_stages = list(STAGES) + ["live"]

    if stage not in valid_stages:
        raise SystemExit(
            f"Stage must be one of: {', '.join(valid_stages)}"
        )

    api_key = os.getenv("HINDSIGHT_API_KEY")
    base_url = os.getenv(
        "HINDSIGHT_BASE_URL",
        "https://api.hindsight.vectorize.io",
    )
    base_bank_id = os.getenv(
        "HINDSIGHT_BANK_ID",
        "competitive-intel-demo",
    )

    if not api_key:
        raise SystemExit("HINDSIGHT_API_KEY is missing from .env")

    client = Hindsight(
        base_url=base_url,
        api_key=api_key,
    )

    # Cold / Early / Full use their own historical snapshots.
    #
    # Live starts with the complete Full history.
    # After that, Live becomes the only bank that the application
    # is allowed to modify.
    seed_stage = "full" if stage == "live" else stage

    bank_id = f"{base_bank_id}-{stage}"

    memories = memories_until(STAGES[seed_stage])

    print()
    print("=" * 60)
    print(f"Seeding stage : {stage}")
    print(f"Source stage  : {seed_stage}")
    print(f"Bank          : {bank_id}")
    print(f"Memories      : {len(memories)}")
    print("=" * 60)
    print()

    try:
        for memory in memories:
            client.retain(
                bank_id=bank_id,
                **to_retain_kwargs(memory),
            )

            print(
                f"  retained {memory.id:<10} "
                f"{memory.date}  {memory.kind}"
            )

        print()
        print(f"SUCCESS: {bank_id} seeded.")
        print()

    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python seed_hindsight.py "
            "<cold|early|full|live>"
        )
        raise SystemExit(1)

    main(sys.argv[1])