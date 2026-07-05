#!/usr/bin/env python3
"""Safely evaluate an arithmetic expression.

The expression may be passed as arguments or piped in via stdin. Evaluation
uses Python's AST rather than eval(), so only the whitelisted operators,
functions, and constants below are permitted -- arbitrary code cannot run.
"""

import ast
import math
import operator
import sys

# Binary and unary operators we allow.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Names that may appear in an expression.
_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}
_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}


def _eval(node):
    """Recursively evaluate a parsed AST node, rejecting anything unexpected."""
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func = _FUNCS.get(node.func.id)
        if func is None:
            raise ValueError(f"unknown function: {node.func.id}")
        return func(*[_eval(a) for a in node.args])
    raise ValueError("unsupported expression")


def evaluate(expr):
    tree = ast.parse(expr, mode="eval")
    return _eval(tree)


def main():
    expr = " ".join(sys.argv[1:])
    if not expr and not sys.stdin.isatty():
        expr = sys.stdin.read()
    expr = expr.strip()
    if not expr:
        sys.exit('Usage: calc.py "2 + 2 * 10"')
    try:
        print(evaluate(expr))
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as exc:
        sys.exit(f"error: {exc}")


if __name__ == "__main__":
    main()
