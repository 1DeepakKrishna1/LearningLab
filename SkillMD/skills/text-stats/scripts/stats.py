#!/usr/bin/env python3
"""Print word, line, and character counts for the given text.

Text can be passed as arguments or piped in via stdin.
"""

import sys


def main():
    text = " ".join(sys.argv[1:])
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()

    words = len(text.split())
    lines = len(text.splitlines()) if text else 0
    chars = len(text)

    print(f"words: {words}")
    print(f"lines: {lines}")
    print(f"chars: {chars}")


if __name__ == "__main__":
    main()
