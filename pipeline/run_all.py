import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import enrich_ai, parse


def main():
    parse.main()
    enrich_ai.main()


if __name__ == "__main__":
    main()
