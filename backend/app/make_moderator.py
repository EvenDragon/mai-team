"""Grant the moderator role to an existing account from the server console."""

import argparse

from sqlalchemy import select

from .db import SessionLocal
from .models import User


def main():
    parser = argparse.ArgumentParser(description="Назначить модератора по email")
    parser.add_argument("email")
    email = parser.parse_args().email.strip().lower()
    with SessionLocal.begin() as db:
        account = db.scalar(select(User).where(User.email == email).with_for_update())
        if account is None:
            raise SystemExit(f"Аккаунт {email} не найден. Сначала зарегистрируйте его на сайте.")
        if account.role == "moderator":
            print(f"{email} уже модератор.")
            return
        account.role = "moderator"
    print(f"{email} получил права модератора.")


if __name__ == "__main__":
    main()
