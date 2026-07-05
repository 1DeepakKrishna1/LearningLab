import json

from app_detector.cli import main


def test_pipeline_and_predict_end_to_end(tmp_path, capsys):
    master = tmp_path / "master.json"
    training = tmp_path / "training.json"
    model = tmp_path / "model.json"

    rc = main([
        "pipeline",
        "--master-count", "150",
        "--training-count", "80",
        "--master", str(master),
        "--training", str(training),
        "--model", str(model),
    ])
    assert rc == 0
    assert master.exists() and training.exists() and model.exists()

    out = capsys.readouterr().out
    decision = json.loads(out)  # the final sample prediction is printed to stdout
    assert decision["application_id"].startswith("APP-")

    # Now predict from a sampled training row.
    rc = main(["predict", "--model", str(model), "--random-from", str(training), "--seed", "1"])
    assert rc == 0
    decision = json.loads(capsys.readouterr().out)
    assert set(decision) == {
        "application_id", "ai_decision", "recommended_action", "confidence", "signals"
    }


def test_predict_inline_features(tmp_path, capsys):
    master = tmp_path / "m.json"
    training = tmp_path / "t.json"
    model = tmp_path / "mod.json"
    main(["generate-master", "--count", "100", "--out", str(master)])
    main(["generate-training", "--master", str(master), "--count", "60", "--out", str(training)])
    main(["train", "--training", str(training), "--model", str(model)])
    capsys.readouterr()

    features = {
        "employment_status": "employed",
        "income_bracket": "high",
        "credit_history": "good",
        "loan_purpose": "home",
        "residence_type": "own",
        "region": "north",
        "existing_customer": "yes",
        "device_type": "mobile",
    }
    rc = main(["predict", "--model", str(model), "--features", json.dumps(features)])
    assert rc == 0
    decision = json.loads(capsys.readouterr().out)
    assert decision["application_id"].startswith("APP-")


def test_predict_requires_exactly_one_input(tmp_path):
    model = tmp_path / "mod.json"
    master = tmp_path / "m.json"
    training = tmp_path / "t.json"
    main(["generate-master", "--count", "50", "--out", str(master)])
    main(["generate-training", "--master", str(master), "--count", "40", "--out", str(training)])
    main(["train", "--training", str(training), "--model", str(model)])
    # No input source provided -> error exit code 1.
    assert main(["predict", "--model", str(model)]) == 1


def test_evaluate_reports_accuracy(tmp_path, capsys):
    master = tmp_path / "m.json"
    training = tmp_path / "t.json"
    model = tmp_path / "mod.json"
    main(["generate-master", "--count", "100", "--out", str(master)])
    main(["generate-training", "--master", str(master), "--count", "80",
          "--noise", "0.0", "--out", str(training)])
    main(["train", "--training", str(training), "--model", str(model)])
    capsys.readouterr()

    rc = main(["evaluate", "--model", str(model), "--dataset", str(training)])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["total"] == 80
    # With zero noise the model should classify the training set near-perfectly.
    assert report["accuracy"] >= 0.95
