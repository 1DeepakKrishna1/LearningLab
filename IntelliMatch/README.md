# IntelliMatch

Fill PLP cross-reference match columns in an Excel workbook using previously
learned matches. Exact key lookups run first; anything left over falls back to a
semantic (embedding) nearest-key search.

## How it works

The pipeline has two scripts:

1. **`generate_dictionaries.py`** — reads a labeled cross-reference CSV and
   builds two JSON lookup dictionaries:
   - `system_dictionary.json` — machine matches (`PLP Cross Part`,
     `Confidence Score`, `Reason of Match`).
   - `human_dictionary.json` — human-verified matches (`H_PLPMatch`,
     `H_MatchReason`, and a fixed `Confidence Score` of `95%`).

   Both dictionaries are keyed by `"<manufacturer_part_number>|<manufacturer>|<description>"`.
   Reruns **merge** into the existing JSON files rather than overwriting them.

2. **`fill_matches.py`** — reads an input `.xlsx`, builds the same key per row,
   and fills three columns: `PLP Cross Part`, `Confidence Score`,
   `Reason of Match`.
   - First it tries an **exact key** lookup (Human dictionary preferred, then
     System).
   - Rows with no exact match fall back to a **semantic nearest-key** search:
     the row key is embedded with a `SentenceTransformer` and compared by cosine
     similarity against every dictionary key. The nearest key at or above
     `SIMILARITY_THRESHOLD` wins (Human preferred), and its reason is annotated
     with the matched key and score.
   - Rows that clear nothing are left unchanged.

### Safety guard

`fill_matches.py` refuses to touch the workbook if **any** of the five result
columns (`PLP Cross Part`, `Confidence Score`, `Reason of Match`, `H_PLPMatch`,
`H_MatchReason`) already contains data. This prevents accidentally overwriting a
partially processed file. The input workbook must contain all five columns plus
the three key columns.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # PowerShell / cmd on Windows
pip install -r requirements.txt
```

## Configuration

`fill_matches.py` reads its settings from a `.env` file in this folder (via
[python-dotenv](https://pypi.org/project/python-dotenv/)). Copy `.env.example`
to `.env` and adjust as needed. Any value can also be supplied as a normal
environment variable, which takes precedence at the shell level.

| Variable               | Default            | Description                                                              |
| ---------------------- | ------------------ | ------------------------------------------------------------------------ |
| `EMBED_MODEL`          | `all-MiniLM-L6-v2` | SentenceTransformer model used for the semantic nearest-key fallback.    |
| `SIMILARITY_THRESHOLD` | `0.80`             | Minimum cosine similarity (0.0–1.0) to accept a semantic match.          |
| `USE_SEMANTIC_SEARCH`  | `true`             | Enable the semantic fallback. When `false`, only exact matches are used. |

`USE_SEMANTIC_SEARCH` accepts `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`.

## Usage

Build (or update) the dictionaries from a labeled CSV:

```bash
python generate_dictionaries.py input.csv
```

Fill matches into a workbook (edited in place):

```bash
python fill_matches.py test.xlsx
```

Example output:

```
Done: 3 exact + 1 semantic from Human, 5 exact + 2 semantic from System, 4 unmatched -> test.xlsx
```

## Files

| File                       | Purpose                                              |
| -------------------------- | ---------------------------------------------------- |
| `generate_dictionaries.py` | Build/merge the System & Human dictionaries from CSV |
| `fill_matches.py`          | Fill match columns in an `.xlsx`                     |
| `system_dictionary.json`   | Machine-match lookup (generated)                     |
| `human_dictionary.json`    | Human-verified lookup (generated)                    |
| `.env` / `.env.example`    | Runtime configuration                                |
| `requirements.txt`         | Python dependencies                                  |

## Notes

- The workbook is modified **in place**, so keep a backup of important inputs.
- The first run downloads the embedding model (`EMBED_MODEL`); subsequent runs
  use the cached copy.
