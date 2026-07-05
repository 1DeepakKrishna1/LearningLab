"""
Generate System and Human dictionaries from the PLP cross-reference CSV.

Key  : "<manufacturer_part_number>|<manufacturer>|<description>"
System value : {"PLP Cross Part", "Confidence Score", "Reason of Match"}
Human value  : {"H_PLPMatch", "H_MatchReason", "Confidence Score": "95%"}

Rows with an empty "PLP Cross Part" are skipped for the System dict.
Rows with an empty "H_PLPMatch" are skipped for the Human dict.
"""

import csv
import json
import os
import sys

SYSTEM_JSON = "system_dictionary.json"
HUMAN_JSON = "human_dictionary.json"


def clean(value):
    """Normalize a cell: treat None/whitespace as empty string."""
    return (value or "").strip()


def load_existing(path):
    """Load an existing JSON dictionary, or return an empty dict if absent/empty."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}


def build_dictionaries(csv_path, system_dict=None, human_dict=None):
    # Start from the existing dictionaries so reruns merge instead of overwrite:
    # new keys are added, existing keys are updated with the latest CSV values.
    system_dict = {} if system_dict is None else system_dict
    human_dict = {} if human_dict is None else human_dict

    # utf-8-sig strips the leading BOM (ï»¿) present in the file.
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            part_number = clean(row.get("manufacturer_part_number"))
            manufacturer = clean(row.get("manufacturer"))
            description = clean(row.get("description"))

            key = f"{part_number}|{manufacturer}|{description}"

            plp_cross_part = clean(row.get("PLP Cross Part"))
            confidence_score = clean(row.get("Confidence Score"))
            reason_of_match = clean(row.get("Reason of Match"))

            h_plp_match = clean(row.get("H_PLPMatch"))
            h_match_reason = clean(row.get("H_MatchReason"))

            # System dictionary: include only if PLP Cross Part is present.
            if plp_cross_part:
                system_dict[key] = {
                    "PLP Cross Part": plp_cross_part,
                    "Confidence Score": confidence_score,
                    "Reason of Match": reason_of_match,
                }

            # Human dictionary: include only if H_PLPMatch is present.
            if h_plp_match:
                human_dict[key] = {
                    "H_PLPMatch": h_plp_match,
                    "H_MatchReason": h_match_reason,
                    "Confidence Score": "95%",
                }

    return system_dict, human_dict


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_dictionaries.py <input.csv>")
        sys.exit(1)

    input_csv = sys.argv[1]
    if not os.path.exists(input_csv):
        print(f"ERROR: file not found: {input_csv}")
        sys.exit(1)

    # Load any previously generated dictionaries so this run merges into them.
    system_dict = load_existing(SYSTEM_JSON)
    human_dict = load_existing(HUMAN_JSON)

    system_dict, human_dict = build_dictionaries(input_csv, system_dict, human_dict)

    with open(SYSTEM_JSON, "w", encoding="utf-8") as f:
        json.dump(system_dict, f, indent=2, ensure_ascii=False)

    with open(HUMAN_JSON, "w", encoding="utf-8") as f:
        json.dump(human_dict, f, indent=2, ensure_ascii=False)

    print(f"System dictionary: {len(system_dict)} entries -> {SYSTEM_JSON}")
    print(f"Human dictionary : {len(human_dict)} entries -> {HUMAN_JSON}")


if __name__ == "__main__":
    main()
