---
name: password-gen
description: Generate strong random passwords. Use this skill whenever the user wants to create, generate, or make a password, a passphrase, or a secure random secret or token.
entrypoint: scripts/passgen.py
---

# Password Gen

Generate cryptographically strong random passwords using Python's `secrets`
module.

## Usage

```bash
passgen.py                       # one 16-char password
passgen.py --length 24           # set length
passgen.py --count 5             # generate several at once
passgen.py --no-symbols          # letters + digits only
passgen.py --words 4             # a dice-style passphrase instead
```
