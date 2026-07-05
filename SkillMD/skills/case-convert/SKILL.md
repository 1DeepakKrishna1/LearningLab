---
name: case-convert
description: Convert text between letter cases and identifier styles. Use this skill whenever the user wants to change text to uppercase, lowercase, title case, snake_case, kebab-case, camelCase, or PascalCase, or asks to reformat the casing of a string or variable name.
entrypoint: scripts/caseconv.py
---

# Case Convert

Transform text into a chosen case style. Reads from arguments or stdin.

## Usage

```bash
caseconv.py upper  "hello world"   # HELLO WORLD
caseconv.py lower  "Hello World"   # hello world
caseconv.py title  "hello world"   # Hello World
caseconv.py snake  "Hello World"   # hello_world
caseconv.py kebab  "Hello World"   # hello-world
caseconv.py camel  "hello world"   # helloWorld
caseconv.py pascal "hello world"   # HelloWorld
echo "hello world" | caseconv.py snake
```
