from db import query


def fetch(arg: str) -> str:
    return query(arg)
