# app-detector

A small, **dependency-free** Python CLI that detects an `application_id` from eight
categorical features using a **Categorical Naive Bayes** classifier, then wraps the
prediction in a risk/action decision.

```json
{
  "application_id": "APP-80637",
  "ai_decision": "Low Risk",
  "recommended_action": "Escalate",
  "confidence": 0.76,
  "signals": ["edge_case_flag", "manual_review_recommended"]
}
```

The Naive Bayes model is implemented from scratch (Laplace-smoothed, numerically
stable softmax) in pure standard-library Python — nothing to `pip install` to run it.

## What it does

1. **Master catalog** — generates ~1000 applications, each a unique `application_id`
   (primary key) plus 8 string features.
2. **Training data** — generates ~100 labelled observations (8 features → `application_id`),
   sampled from the catalog with a little per-feature noise so there is signal to learn.
3. **Model** — fits Categorical Naive Bayes and predicts the most probable
   `application_id`. The posterior probability becomes `confidence`; risk tier, recommended
   action, and explainability `signals` are derived from confidence and match quality.

## Features (the 8 inputs)

`employment_status`, `income_bracket`, `credit_history`, `loan_purpose`,
`residence_type`, `region`, `existing_customer`, `device_type`.

Run `app-detector features` to see all allowed values.

## Install

```bash
pip install -e .          # editable install, exposes the `app-detector` command
# or run without installing:
python -m app_detector --help
```

## Quick start

The fastest path — generate data, train, evaluate, and show a sample prediction:

```bash
app-detector pipeline
```

Or run the steps individually:

```bash
app-detector generate-master   --count 1000 --out master.json
app-detector generate-training --master master.json --count 100 --out training.json
app-detector train             --training training.json --model model.json
app-detector evaluate          --model model.json --dataset training.json
```

## Retraining with human-in-the-loop feedback

Already have a trained `model.json` and a batch of additional labelled records
(e.g. human-reviewed corrections in `hitl.json`)? Fold them into the existing
model without retraining from scratch:

```bash
# Update model.json in place with the extra records:
app-detector retrain --training hitl.json --model model.json

# Or write the updated model to a new file, leaving the original untouched:
app-detector retrain --training hitl.json --model model.json --out model.v2.json
```

`hitl.json` may be **a single record object or a JSON array of records**, each
with the 8 features plus the true `application_id` (same shape as
`training.json`). Because the classifier is count-based, this incremental update
is exact: the result is identical to training on the original corpus
concatenated with the HITL records, and any `application_id` not previously seen
is added as a new class automatically.

### Making a correction "stick" (`--weight`)

A single HITL record competes against ~100 prior observations, so on its own it
nudges confidence only a little (often into Medium Risk). When you trust a
correction and want it to dominate, count it multiple times with `--weight`:

```bash
app-detector retrain --training hitl.json --model model.json --weight 5
```

`--weight N` folds each record in `N` times. For this model, `--weight 3` lifts a
correction to ~0.95 confidence (Low Risk), and `--weight 5` to ~0.99. Use it
sparingly — a very high weight makes that label nearly certain for its exact
feature profile.

## Predicting

```bash
# From inline JSON:
app-detector predict --model model.json --features '{
  "employment_status": "employed", "income_bracket": "high", "credit_history": "good",
  "loan_purpose": "home", "residence_type": "own", "region": "north",
  "existing_customer": "yes", "device_type": "mobile"}'

# From a JSON file:
app-detector predict --model model.json --input my_features.json

# Sample a random row from a dataset (handy for demos):
app-detector predict --model model.json --random-from training.json
```

## HTTP API (FastAPI)

The same `predict` and `retrain` logic is exposed over HTTP for embedding in
other services. Install the API extras and start the server on **port 9000**:

```bash
pip install -e ".[api]"
app-detector-api                      # serves on 0.0.0.0:9000
# or: uvicorn app_detector.api:app --port 9000
```

The model file it reads/writes defaults to `model.json`; override with the
`APP_DETECTOR_MODEL` env var (host/port via `APP_DETECTOR_HOST` /
`APP_DETECTOR_PORT`). Interactive docs live at http://localhost:9000/docs.

| Method & path | Purpose |
|---------------|---------|
| `GET  /health`   | Liveness + the model path in use. |
| `GET  /features` | The feature schema (allowed values). |
| `POST /predict`  | Body: the 8 features. Returns the decision payload. |
| `POST /retrain`  | Body: `{ "records": <record or [records]>, "weight": N }`. Folds records into the model, persists it, returns a summary. |

```bash
# Predict:
curl -s -X POST http://localhost:9000/predict \
  -H "Content-Type: application/json" \
  -d '{"employment_status":"employed","income_bracket":"high","credit_history":"good",
       "loan_purpose":"home","residence_type":"own","region":"north",
       "existing_customer":"yes","device_type":"mobile"}'

# Retrain with an upweighted HITL correction (persists to the server's model file):
curl -s -X POST http://localhost:9000/retrain \
  -H "Content-Type: application/json" \
  -d '{"weight":5,"records":{"employment_status":"employed","income_bracket":"high",
       "credit_history":"none","loan_purpose":"home","residence_type":"family",
       "region":"north","existing_customer":"no","device_type":"desktop",
       "application_id":"APP-66237"}}'
```

`/retrain` accepts either a single record object or a list, and `weight` works
exactly like the CLI's `--weight`.

## Decision logic

| Confidence (top posterior) | Risk tier     |
|----------------------------|---------------|
| ≥ 0.75                     | Low Risk      |
| 0.50 – 0.75                | Medium Risk   |
| < 0.50                     | High Risk     |

**Signals** are raised for ambiguous or weak matches:
`edge_case_flag` (top two classes nearly tied), `manual_review_recommended`
(borderline confidence, 0.35–0.50, that a human can likely resolve),
`low_confidence_match` (< 0.35, too weak to act on), `profile_mismatch` (an input
value never seen for the predicted id), `sparse_training_signal`, and
`strong_profile_match`.

**Recommended action**: anything flagged for review or ambiguity → `Escalate`;
otherwise High Risk → `Decline` (confidence too weak to identify the application),
Low Risk → `Approve`, Medium Risk → `Escalate`. Risk and action are intentionally
decoupled — a Low Risk match can still be escalated when a signal fires (as in the
example payload above).

## Project layout

```
src/app_detector/
  config.py     feature schema + decision thresholds
  datagen.py    master & training data generation (seeded, reproducible)
  nb.py         Categorical Naive Bayes (fit / predict / serialise)
  decision.py   prediction -> risk/action/signals payload
  model.py      train / save / load / evaluate orchestration
  cli.py        argparse command-line interface
  api.py        FastAPI HTTP interface (predict + retrain, port 9000)
tests/          pytest suite
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```
