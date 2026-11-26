import os
import psycopg
from .migrate import ROOT


def seed():
    if os.getenv("ALLOW_DEMO_SEED") != "true":
        raise RuntimeError(
            "Demo seed is disabled. Set ALLOW_DEMO_SEED=true only in a demo database."
        )
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as db:
        db.execute((ROOT / "seeds" / "001_demo.sql").read_text(encoding="utf-8-sig"))
    print("Demo data ready")


if __name__ == "__main__":
    seed()
