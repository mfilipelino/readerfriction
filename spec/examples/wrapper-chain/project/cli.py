from handlers import handle


def main(arg: str) -> str:
    return handle(arg)


if __name__ == "__main__":
    import sys

    print(main(sys.argv[1]))
