#!/usr/bin/env python3
"""Generate cryptographically strong random passwords.

Uses the `secrets` module (CSPRNG), not `random`, so output is suitable for
real secrets. Can emit character-based passwords or word-based passphrases.

Usage:
    python passgen.py
    python passgen.py --length 24 --count 5
    python passgen.py --no-symbols
    python passgen.py --words 4
"""

import argparse
import secrets
import string

LETTERS = string.ascii_letters
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{}"

# A small, readable wordlist for passphrases. Real deployments would load a
# larger list (e.g. EFF's), but this keeps the skill self-contained.
WORDS = (
    "able acid aged also area army away baby back ball band bank base bath "
    "bear beat been beer bell belt bird blue boat body bone book boss both "
    "bowl bulk burn bush busy cake call calm came camp card care case cash "
    "cell chat chip city clip club coal coat code cold come cook cool cope "
    "copy core cost crew crop dark data date dawn days dead deal dear debt "
    "deep deny desk dial diet disc disk does done door dose down draw drew "
    "drop drug dual duke dust duty each earn ease east easy edge else even "
    "ever evil exit face fact fail fair fall farm fast fate fear feed feel "
    "feet fell felt file fill film find fine fire firm fish five flat flow "
    "fold folk food foot ford form fort four free from fuel full fund gain "
    "game gate gave gear gene gift girl give glad goal goes gold golf gone "
    "good gray grew grey grow gulf hair half hall hand hang hard harm hate"
).split()


def char_password(length, use_symbols):
    alphabet = LETTERS + DIGITS + (SYMBOLS if use_symbols else "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


def passphrase(word_count):
    return "-".join(secrets.choice(WORDS) for _ in range(word_count))


def main():
    parser = argparse.ArgumentParser(description="Generate strong passwords.")
    parser.add_argument("--length", type=int, default=16,
                        help="password length (default 16)")
    parser.add_argument("--count", type=int, default=1,
                        help="how many to generate (default 1)")
    parser.add_argument("--no-symbols", action="store_true",
                        help="use only letters and digits")
    parser.add_argument("--words", type=int, default=0,
                        help="generate an N-word passphrase instead")
    args = parser.parse_args()

    if args.length < 1 or args.count < 1:
        parser.error("--length and --count must be positive")

    for _ in range(args.count):
        if args.words > 0:
            print(passphrase(args.words))
        else:
            print(char_password(args.length, not args.no_symbols))


if __name__ == "__main__":
    main()
