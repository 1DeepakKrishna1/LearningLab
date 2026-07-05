---
name: json-tool
description: Validate, pretty-print, or minify JSON. Use this skill whenever the user wants to format, prettify, indent, minify, compact, or check or validate some JSON text or a JSON file.
entrypoint: scripts/jsontool.py
---

# JSON Tool

Validate and reformat JSON. Reads from a file, an argument, or stdin.

## Subcommands

```bash
jsontool.py format '{"b":2,"a":1}'   # pretty-print, 2-space indent
jsontool.py minify data.json          # strip whitespace to one line
jsontool.py validate data.json        # report valid / invalid + error
cat data.json | jsontool.py format    # pipe in via stdin
```

Use `--sort-keys` with `format` to sort object keys alphabetically.
