def validate_users(users: list[dict]) -> None:
    for user in users:
        if "id" not in user or not user["id"]:
            raise ValueError(f"user missing id: {user}")


def validate_accounts(accounts: list[dict]) -> None:
    for account in accounts:
        if "owner_id" not in account:
            raise ValueError(f"account missing owner_id: {account}")
