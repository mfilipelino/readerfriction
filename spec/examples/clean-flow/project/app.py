def parse(raw: str) -> list[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [int(p) for p in parts]


def summarise(numbers: list[int]) -> dict[str, float]:
    if not numbers:
        raise ValueError("need at least one number")
    total = sum(numbers)
    return {
        "count": len(numbers),
        "mean": total / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
    }


def main(raw: str) -> str:
    numbers = parse(raw)
    stats = summarise(numbers)
    return f"mean={stats['mean']:.2f} over {stats['count']} items"


if __name__ == "__main__":
    import sys

    print(main(sys.argv[1]))
