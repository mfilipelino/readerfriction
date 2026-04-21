def emit_report(records: list[dict]) -> None:
    for record in records:
        user = record["user"]
        account = record["account"]
        print(f"{user['id']} -> {account['owner_id']}")
