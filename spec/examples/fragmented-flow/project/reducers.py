def merge_records(users: list[dict], accounts: list[dict]) -> list[dict]:
    by_user = {u["id"]: u for u in users}
    out: list[dict] = []
    for account in accounts:
        user = by_user.get(account["owner_id"])
        if user is None:
            continue
        out.append({"user": user, "account": account})
    return out
