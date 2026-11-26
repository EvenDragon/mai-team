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
            paths = sorted((ROOT / "migrations").glob("*.sql"))
            demo_path = ROOT / "seeds" / "vps_demo_001.sql"
            demo_password = os.getenv("VPS_DEMO_PASSWORD")
            if os.getenv("VPS_DEMO_ENABLED") == "true" or demo_password:
                paths.append(demo_path)
            if demo_password and not 10 <= len(demo_password) <= 128:
                raise ValueError("VPS_DEMO_PASSWORD в .env должен содержать от 10 до 128 символов")
            for path in paths:
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
                if path == demo_path:
                    from .security import hash_password

                    db.execute(
                        "SELECT set_config('mai.demo_password_hash', %s, false)",
                        (hash_password(demo_password) if demo_password else "!vps-demo",),
                    )
                # Migration SQL owns its BEGIN/COMMIT. Add bookkeeping into same transaction.
                sql = sql.rsplit("COMMIT;", 1)[0]
                db.execute(sql)
                db.execute(
                    "INSERT INTO schema_migrations VALUES (%s,%s)", (path.name, digest)
                )
                db.execute("COMMIT")
                print(f"Applied {path.name}")
            # Activate only demo profiles originally created without a password.
            if demo_password and db.execute(
                "SELECT 1 FROM users WHERE password_hash = '!vps-demo' LIMIT 1"
            ).fetchone():
                from .security import hash_password

                db.execute(
                    "UPDATE users SET password_hash = %s WHERE password_hash = '!vps-demo'",
                    (hash_password(demo_password),),
                )
        finally:
            db.execute("SELECT pg_advisory_unlock(5152026)")


if __name__ == "__main__":
    migrate()
