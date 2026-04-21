_TABLE = {"alice": "wonderland", "bob": "builder"}


def query(key: str) -> str:
    value = _TABLE.get(key)
    if value is None:
        raise KeyError(key)
    for prefix in ("mr. ", "ms. "):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return f"{key}={value}"
