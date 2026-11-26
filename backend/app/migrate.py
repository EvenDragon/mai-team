"""Versioned SQL migrations, no ORM DDL in the application. Run from backend/."""

import hashlib
import os
from pathlib import Path
import psycopg

ROOT = Path(
    os.getenv("DATABASE_DIR", str(Path(__file__).resolve().parents[2] / "database"))
)


def migrate():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, autocommit=True) as db:
        db.execute("SELECT pg_advisory_lock(5152026)")
        try:
            db.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, checksum text NOT NULL)"
            )
            for path in sorted((ROOT / "migrations").glob("*.sql")):
                sql = path.read_text(encoding="utf-8-sig")
                digest = hashlib.sha256(sql.encode()).hexdigest()
                previous = db.execute(
                    "SELECT checksum FROM schema_migrations WHERE version=%s",
                    (path.name,),
                ).fetchone()
                if previous:
                    if previous[0] != digest:
                        raise RuntimeError(f"Migration modified: {path.name}")
                    continue
                # Migration SQL owns its BEGIN/COMMIT. Add bookkeeping into same transaction.
                sql = sql.rsplit("COMMIT;", 1)[0]
                db.execute(sql)
                db.execute(
                    "INSERT INTO schema_migrations VALUES (%s,%s)", (path.name, digest)
                )
                db.execute("COMMIT")
                print(f"Applied {path.name}")
        finally:
            db.execute("SELECT pg_advisory_unlock(5152026)")


if __name__ == "__main__":
    migrate()
