---
name: calc
description: Evaluate arithmetic and math expressions. Use this skill whenever the user wants to calculate, compute, or evaluate a math expression, do arithmetic, or asks "what is X plus/times/divided by Y".
entrypoint: scripts/calc.py
---

# Calc

Safely evaluate an arithmetic expression and print the result. Supports
`+ - * / // % **`, parentheses, and a handful of common functions and
constants (`sqrt`, `abs`, `round`, `min`, `max`, `pi`, `e`).

It uses Python's AST instead of `eval`, so arbitrary code cannot run.

## Usage

```bash
calc.py "2 + 2 * 10"        # -> 22
calc.py "sqrt(144) + pi"    # -> 15.141592653589793
# or pipe an expression in:  echo "(3 + 4) ** 2" | calc.py
```
