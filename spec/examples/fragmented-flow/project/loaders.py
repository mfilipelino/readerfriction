import csv
from pathlib import Path


def load_users(path: str) -> list[dict]:
    with Path(path, "users.csv").open() as fh:
        return list(csv.DictReader(fh))


def load_accounts(path: str) -> list[dict]:
    with Path(path, "accounts.csv").open() as fh:
        return list(csv.DictReader(fh))
