---
name: text-stats
description: Count words, lines, and characters in a piece of text. Use this skill whenever the user wants text statistics, a word count, character count, or line count, or asks how many words or characters are in something.
entrypoint: scripts/stats.py
---

# Text Stats

Report word, line, and character counts for some text.

## Usage

```bash
stats.py "some text here"   # counts the text passed as arguments
# or pipe text in:  echo "hello" | stats.py
```
