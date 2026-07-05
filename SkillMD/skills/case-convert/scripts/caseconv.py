#!/usr/bin/env python3
"""Convert text between letter cases and identifier styles.

The style is the first argument; the remaining arguments (or stdin) are the
text to convert.

Usage:
    python caseconv.py snake "Hello World"
    echo "Hello World" | python caseconv.py kebab
"""

import re
import sys


def split_words(text):
    """Break text into lowercase words, handling spaces, separators, and
    camelCase / PascalCase boundaries."""
    # Insert spaces at camelCase boundaries: "fooBar" -> "foo Bar".
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    # Split on any run of non-alphanumeric characters.
    words = re.findall(r"[A-Za-z0-9]+", text)
    return [w.lower() for w in words]


def convert(style, text):
    if style == "upper":
        return text.upper()
    if style == "lower":
        return text.lower()
    if style == "title":
        return " ".join(w.capitalize() for w in split_words(text))

    words = split_words(text)
    if style == "snake":
        return "_".join(words)
    if style == "kebab":
        return "-".join(words)
    if style == "camel":
        return words[0] + "".join(w.capitalize() for w in words[1:]) if words else ""
    if style == "pascal":
        return "".join(w.capitalize() for w in words)
    raise ValueError(f"unknown style: {style}")


STYLES = ["upper", "lower", "title", "snake", "kebab", "camel", "pascal"]


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in STYLES:
        sys.exit(f"Usage: caseconv.py <{'|'.join(STYLES)}> \"text\"")

    style = sys.argv[1]
    text = " ".join(sys.argv[2:])
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        sys.exit("error: no text provided")

    print(convert(style, text))


if __name__ == "__main__":
    main()
