#!/usr/bin/env python3
"""Validate, pretty-print, or minify JSON.

The input source for every subcommand is resolved the same way: if a positional
argument is given and names an existing file, its contents are read; otherwise
the argument itself is treated as the JSON text; if no argument is given, JSON
is read from stdin.

Usage:
    python jsontool.py format '{"b":2,"a":1}'
    python jsontool.py format data.json --sort-keys
    python jsontool.py minify data.json
    python jsontool.py validate data.json
    cat data.json | python jsontool.py format
"""

import argparse
import json
import sys
from pathlib import Path


def read_input(source):
    """Resolve the JSON text from a file path, a literal string, or stdin."""
    if source:
        path = Path(source)
        if path.exists():
            return path.read_text()
        return source
    if not sys.stdin.isatty():
        return sys.stdin.read()
    sys.exit("error: no JSON provided (pass a file, a string, or pipe stdin)")


def parse(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        sys.exit(f"invalid JSON: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Validate or reformat JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_format = sub.add_parser("format", help="pretty-print with indentation")
    p_format.add_argument("source", nargs="?", help="file path or JSON string")
    p_format.add_argument("--indent", type=int, default=2, help="indent width")
    p_format.add_argument("--sort-keys", action="store_true",
                          help="sort object keys alphabetically")

    p_minify = sub.add_parser("minify", help="compact onto a single line")
    p_minify.add_argument("source", nargs="?", help="file path or JSON string")

    p_validate = sub.add_parser("validate", help="check whether input is valid")
    p_validate.add_argument("source", nargs="?", help="file path or JSON string")

    args = parser.parse_args()
    text = read_input(args.source)

    if args.command == "validate":
        parse(text)  # exits with a message if invalid
        print("valid JSON")
    elif args.command == "format":
        data = parse(text)
        print(json.dumps(data, indent=args.indent, sort_keys=args.sort_keys,
                         ensure_ascii=False))
    elif args.command == "minify":
        data = parse(text)
        print(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
