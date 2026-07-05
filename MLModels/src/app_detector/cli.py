"""Command-line interface for app-detector.

Subcommands
-----------
  generate-master    Build the master catalog (~1000 applications).
  generate-training  Build labelled training observations (~100 rows).
  train              Fit a Naive Bayes model from training data.
  retrain            Fold additional (e.g. HITL) records into a trained model.
  predict            Detect an application_id + decision for a feature input.
  evaluate           Report top-1 accuracy of a model on a labelled set.
  pipeline           Run generate -> train -> evaluate end to end.
  features           Print the feature schema.

Run ``app-detector <subcommand> --help`` for per-command options.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from typing import Dict, List, Optional, Sequence

from . import __version__
from .config import FEATURES
from .datagen import generate_master, generate_training
from .decision import build_decision
from .io_utils import read_json, write_json
from .model import (
    LABEL_KEY,
    evaluate,
    extract_features,
    load_model,
    retrain_model,
    save_model,
    train_model,
)


def _eprint(*args) -> None:
    print(*args, file=sys.stderr)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_generate_master(args: argparse.Namespace) -> int:
    records = generate_master(count=args.count, seed=args.seed)
    write_json(args.out, records)
    _eprint(f"Wrote {len(records)} master records -> {args.out}")
    return 0


def cmd_generate_training(args: argparse.Namespace) -> int:
    master = read_json(args.master)
    records = generate_training(
        master,
        count=args.count,
        seed=args.seed,
        pool_size=args.pool_size,
        noise=args.noise,
    )
    write_json(args.out, records)
    distinct = len({r[LABEL_KEY] for r in records})
    _eprint(f"Wrote {len(records)} training records ({distinct} distinct ids) -> {args.out}")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    training = read_json(args.training)
    model = train_model(training, alpha=args.alpha)
    save_model(model, args.model)
    _eprint(
        f"Trained Naive Bayes on {model.n_samples_} records, "
        f"{len(model.classes_)} classes -> {args.model}"
    )
    return 0


def cmd_retrain(args: argparse.Namespace) -> int:
    out = args.out or args.model  # default: update the model in place
    model = load_model(args.model)
    before = model.n_samples_
    classes_before = len(model.classes_)
    data = read_json(args.training)
    # Accept either a JSON array of records or a single record object.
    records = [data] if isinstance(data, dict) else data
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise ValueError(
            f"{args.training} must be a JSON object or array of objects, "
            f"each with the 8 features plus '{LABEL_KEY}'"
        )
    if not records:
        raise ValueError(f"{args.training} contains no records")
    retrain_model(model, records, weight=args.weight)
    save_model(model, out)
    new_classes = len(model.classes_) - classes_before
    weight_note = f" (weight {args.weight})" if args.weight != 1 else ""
    _eprint(
        f"Retrained on {len(records)} additional records{weight_note} "
        f"({before} -> {model.n_samples_} samples, "
        f"{new_classes} new class{'es' if new_classes != 1 else ''}, "
        f"{len(model.classes_)} total) -> {out}"
    )
    return 0


def _resolve_prediction_input(args: argparse.Namespace) -> Dict[str, str]:
    """Build the feature dict from --input, --features, or --random."""
    sources = [bool(args.input), bool(args.features), bool(args.random_from)]
    if sum(sources) != 1:
        raise ValueError("provide exactly one of --input, --features, or --random-from")

    if args.input:
        record = read_json(args.input)
    elif args.features:
        record = json.loads(args.features)
    else:  # --random-from: sample a row from a dataset (handy for demos)
        dataset = read_json(args.random_from)
        if not dataset:
            raise ValueError(f"{args.random_from} is empty")
        rng = random.Random(args.seed)
        record = rng.choice(dataset)
        _eprint(f"Sampled input (true id: {record.get(LABEL_KEY, 'n/a')}): "
                f"{json.dumps({k: record[k] for k in FEATURES})}")
    return extract_features(record)


def cmd_predict(args: argparse.Namespace) -> int:
    model = load_model(args.model)
    features = _resolve_prediction_input(args)
    decision = build_decision(model, features)
    print(json.dumps(decision, indent=2))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    model = load_model(args.model)
    records = read_json(args.dataset)
    report = evaluate(model, records)
    print(json.dumps(report, indent=2))
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    """End-to-end demo: generate data, train, evaluate, and show one prediction."""
    master = generate_master(count=args.master_count, seed=args.seed)
    write_json(args.master, master)
    _eprint(f"[1/4] master:   {len(master)} records -> {args.master}")

    training = generate_training(
        master, count=args.training_count, seed=args.seed + 1, noise=args.noise
    )
    write_json(args.training, training)
    distinct = len({r[LABEL_KEY] for r in training})
    _eprint(f"[2/4] training: {len(training)} records ({distinct} ids) -> {args.training}")

    model = train_model(training, alpha=args.alpha)
    save_model(model, args.model)
    _eprint(f"[3/4] trained:  {len(model.classes_)} classes -> {args.model}")

    report = evaluate(model, training)
    _eprint(f"[4/4] train-set accuracy: {report['accuracy']:.2%} "
            f"({report['correct']}/{report['total']})")

    rng = random.Random(args.seed + 2)
    sample = rng.choice(training)
    decision = build_decision(model, extract_features(sample))
    _eprint(f"\nSample prediction (true id: {sample[LABEL_KEY]}):")
    print(json.dumps(decision, indent=2))
    return 0


def cmd_features(_: argparse.Namespace) -> int:
    print(json.dumps({name: list(values) for name, values in FEATURES.items()}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app-detector",
        description="Naive Bayes application_id detection with risk/action decisioning.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate-master
    p = sub.add_parser("generate-master", help="Generate the master application catalog.")
    p.add_argument("--count", type=int, default=1000, help="Number of applications (default: 1000).")
    p.add_argument("--seed", type=int, default=42, help="Random seed (default: 42).")
    p.add_argument("--out", default="master.json", help="Output path (default: master.json).")
    p.set_defaults(func=cmd_generate_master)

    # generate-training
    p = sub.add_parser("generate-training", help="Generate labelled training observations.")
    p.add_argument("--master", default="master.json", help="Master catalog path (default: master.json).")
    p.add_argument("--count", type=int, default=100, help="Number of training rows (default: 100).")
    p.add_argument("--seed", type=int, default=7, help="Random seed (default: 7).")
    p.add_argument("--pool-size", type=int, default=None,
                   help="How many master apps to draw labels from (default: count//3).")
    p.add_argument("--noise", type=float, default=0.15,
                   help="Per-feature noise probability, 0..1 (default: 0.15).")
    p.add_argument("--out", default="training.json", help="Output path (default: training.json).")
    p.set_defaults(func=cmd_generate_training)

    # train
    p = sub.add_parser("train", help="Train a Naive Bayes model from training data.")
    p.add_argument("--training", default="training.json", help="Training data path (default: training.json).")
    p.add_argument("--model", default="model.json", help="Output model path (default: model.json).")
    p.add_argument("--alpha", type=float, default=1.0, help="Laplace smoothing alpha (default: 1.0).")
    p.set_defaults(func=cmd_train)

    # retrain
    p = sub.add_parser("retrain", help="Apply additional (e.g. HITL) records on top of a trained model.")
    p.add_argument("--model", default="model.json", help="Existing trained model path (default: model.json).")
    p.add_argument("--training", default="hitl.json", help="Additional training records to fold in (default: hitl.json).")
    p.add_argument("--out", default=None, help="Where to write the updated model (default: overwrite --model).")
    p.add_argument("--weight", type=int, default=1,
                   help="Count each record this many times to upweight trusted corrections (default: 1).")
    p.set_defaults(func=cmd_retrain)

    # predict
    p = sub.add_parser("predict", help="Detect an application_id + decision for a feature input.")
    p.add_argument("--model", default="model.json", help="Model path (default: model.json).")
    p.add_argument("--input", help="Path to a JSON file holding the feature object.")
    p.add_argument("--features", help="Inline JSON object of features.")
    p.add_argument("--random-from", help="Sample a random feature row from this dataset file.")
    p.add_argument("--seed", type=int, default=0, help="Seed for --random-from (default: 0).")
    p.set_defaults(func=cmd_predict)

    # evaluate
    p = sub.add_parser("evaluate", help="Report top-1 accuracy on a labelled dataset.")
    p.add_argument("--model", default="model.json", help="Model path (default: model.json).")
    p.add_argument("--dataset", default="training.json", help="Labelled dataset path (default: training.json).")
    p.set_defaults(func=cmd_evaluate)

    # pipeline
    p = sub.add_parser("pipeline", help="Run generate -> train -> evaluate end to end.")
    p.add_argument("--master-count", type=int, default=1000, help="Master size (default: 1000).")
    p.add_argument("--training-count", type=int, default=100, help="Training size (default: 100).")
    p.add_argument("--noise", type=float, default=0.15, help="Training noise (default: 0.15).")
    p.add_argument("--alpha", type=float, default=1.0, help="Laplace alpha (default: 1.0).")
    p.add_argument("--seed", type=int, default=42, help="Base random seed (default: 42).")
    p.add_argument("--master", default="master.json", help="Master output path.")
    p.add_argument("--training", default="training.json", help="Training output path.")
    p.add_argument("--model", default="model.json", help="Model output path.")
    p.set_defaults(func=cmd_pipeline)

    # features
    p = sub.add_parser("features", help="Print the feature schema.")
    p.set_defaults(func=cmd_features)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        _eprint(f"error: {exc}")
        return 1
    except BrokenPipeError:  # pragma: no cover - piping into head etc.
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
