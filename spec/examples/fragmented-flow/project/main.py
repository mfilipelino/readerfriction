from loaders import load_users, load_accounts
from validators import validate_users, validate_accounts
from reducers import merge_records
from reporters import emit_report


def main(path: str) -> None:
    users = load_users(path)
    accounts = load_accounts(path)
    validate_users(users)
    validate_accounts(accounts)
    records = merge_records(users, accounts)
    emit_report(records)


if __name__ == "__main__":
    import sys

    main(sys.argv[1])
