"""
seed_fd_workflow.py
────────────────────────────────────────────────────────────────────────────────
Creates and tests the "Fixed Deposit Opening" workflow:
  1. POST /data-models   → Fixed Deposit data model (7 entities, 2 fields each)
  2. POST /workflows     → FD workflow (Start + 7 agents + End, with invoke params)
  3. POST /associations  → Links workflow ↔ data model
  4. POST /execution     → Runs the workflow
  5. Prints data model state after each step, showing field evolution

Run with: python seed_fd_workflow.py
"""

import json
import sys
import urllib.request
import urllib.error

# Force UTF-8 output on Windows to allow Unicode symbols
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _req(method: str, path: str, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  X {method} {path} -> HTTP {e.code}: {err[:200]}")
        sys.exit(1)


def _color(code: str) -> str:
    colors = {"green": "\033[92m", "yellow": "\033[93m", "cyan": "\033[96m",
              "bold": "\033[1m", "reset": "\033[0m", "red": "\033[91m",
              "violet": "\033[95m"}
    return colors.get(code, "")


C = _color
R = C("reset")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data Model Definition
# ─────────────────────────────────────────────────────────────────────────────

DATA_MODEL_PAYLOAD = {
    "name": "Fixed Deposit",
    "description": "Runtime data model for the Fixed Deposit Opening process. Tracks application, KYC, risk, FD configuration, maturity, compliance, and account creation.",
    "entities": [
        {
            "name": "ApplicationInfo",
            "description": "Applicant data collection tracking",
            "fields": [
                {
                    "name": "records_collected",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of applicant records collected by data ingestion agent",
                    "default_value": 0
                },
                {
                    "name": "data_errors",
                    "field_type": "number",
                    "required": False,
                    "description": "Count of data quality errors found during collection",
                    "default_value": 0
                }
            ]
        },
        {
            "name": "KYCVerification",
            "description": "KYC and document verification tracking",
            "fields": [
                {
                    "name": "kyc_decisions",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of KYC decisions made by role-based approver",
                    "default_value": 0
                },
                {
                    "name": "escalated_cases",
                    "field_type": "number",
                    "required": False,
                    "description": "Number of KYC cases escalated for manual review",
                    "default_value": 0
                }
            ]
        },
        {
            "name": "RiskProfile",
            "description": "Eligibility and risk assessment results",
            "fields": [
                {
                    "name": "records_assessed",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of applicant records assessed for eligibility and risk",
                    "default_value": 0
                },
                {
                    "name": "assessment_errors",
                    "field_type": "number",
                    "required": False,
                    "description": "Count of errors during risk assessment",
                    "default_value": 0
                }
            ]
        },
        {
            "name": "FDConfiguration",
            "description": "Fixed Deposit terms configuration tracking",
            "fields": [
                {
                    "name": "sub_tasks_created",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of FD configuration sub-tasks created by orchestrator",
                    "default_value": 0
                },
                {
                    "name": "sub_tasks_completed",
                    "field_type": "number",
                    "required": False,
                    "description": "Number of FD configuration sub-tasks completed",
                    "default_value": 0
                }
            ]
        },
        {
            "name": "MaturityDetails",
            "description": "Maturity and returns calculation results",
            "fields": [
                {
                    "name": "records_computed",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of maturity computation records processed",
                    "default_value": 0
                },
                {
                    "name": "computation_errors",
                    "field_type": "number",
                    "required": False,
                    "description": "Errors encountered during maturity calculation",
                    "default_value": 0
                }
            ]
        },
        {
            "name": "ComplianceRecord",
            "description": "Compliance audit and review outcomes",
            "fields": [
                {
                    "name": "compliance_decisions",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of compliance audit decisions made",
                    "default_value": 0
                },
                {
                    "name": "compliance_escalated",
                    "field_type": "number",
                    "required": False,
                    "description": "Number of compliance cases escalated",
                    "default_value": 0
                }
            ]
        },
        {
            "name": "AccountSetup",
            "description": "FD account creation results",
            "fields": [
                {
                    "name": "accounts_processed",
                    "field_type": "number",
                    "required": True,
                    "description": "Number of FD accounts successfully created",
                    "default_value": 0
                },
                {
                    "name": "setup_errors",
                    "field_type": "number",
                    "required": False,
                    "description": "Number of account creation errors",
                    "default_value": 0
                }
            ]
        }
    ],
    "relationships": []
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Workflow Definition
#    Invoke output param `name` must match a key in the fake step output.
#    automatic   → processed, errors
#    role_based  → decisions, escalated
#    orchestrator→ sub_tasks_created, sub_tasks_completed
# ─────────────────────────────────────────────────────────────────────────────

def build_workflow_payload():
    return {
        "name": "Fixed Deposit Opening",
        "description": "End-to-end process for opening a Fixed Deposit account: applicant collection, KYC, risk assessment, FD configuration, maturity calculation, compliance audit, and account creation.",
        "status": "active",
        "tags": ["banking", "fixed-deposit", "retail"],
        "nodes": [
            # ── Node 1: Workflow Start ────────────────────────────
            {
                "id": "fd-n1",
                "node_kind": "agent",
                "agent_id": "agent-start",
                "position": {"x": 80, "y": 220},
                "data": {
                    "name": "Workflow Start",
                    "type": "start",
                    "description": "Initialise FD opening workflow",
                    "properties": {
                        "environment": "production",
                        "version": "1.0.0",
                        "run_label": "FD Opening"
                    },
                    "invoke": {
                        "input_parameters": [],
                        "output_parameters": []
                    }
                }
            },

            # ── Node 2: Collect Applicant Details ─────────────────
            {
                "id": "fd-n2",
                "node_kind": "agent",
                "agent_id": "agent-001",
                "position": {"x": 340, "y": 220},
                "data": {
                    "name": "Collect Applicant Details",
                    "type": "automatic",
                    "description": "Ingest applicant personal info, documents, and bank details via API",
                    "properties": {"batch_size": 500, "retry_on_failure": True},
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "workflow_status",
                                "value_type": "workflow",
                                "value": "{{wf.status}}",
                                "description": "Current workflow execution status"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "processed",
                                "value_type": "data_model",
                                "value": "{{ApplicationInfo.records_collected}}",
                                "description": "Write collected record count to ApplicationInfo"
                            },
                            {
                                "name": "errors",
                                "value_type": "data_model",
                                "value": "{{ApplicationInfo.data_errors}}",
                                "description": "Write error count to ApplicationInfo"
                            }
                        ]
                    }
                }
            },

            # ── Node 3: KYC & Document Verification ───────────────
            {
                "id": "fd-n3",
                "node_kind": "agent",
                "agent_id": "agent-009",
                "position": {"x": 600, "y": 220},
                "data": {
                    "name": "KYC & Document Verification",
                    "type": "role_based",
                    "description": "Role-based KYC approval: verifies PAN, Aadhaar, and address proof",
                    "properties": {"roles": ["kyc_officer", "compliance"], "require_all": False},
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "application_records",
                                "value_type": "data_model",
                                "value": "{{ApplicationInfo.records_collected}}",
                                "description": "Number of applicant records to verify"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "decisions",
                                "value_type": "data_model",
                                "value": "{{KYCVerification.kyc_decisions}}",
                                "description": "Write KYC decision count to KYCVerification"
                            },
                            {
                                "name": "escalated",
                                "value_type": "data_model",
                                "value": "{{KYCVerification.escalated_cases}}",
                                "description": "Write escalated KYC case count"
                            }
                        ]
                    }
                }
            },

            # ── Node 4: Eligibility & Risk Check ──────────────────
            {
                "id": "fd-n4",
                "node_kind": "agent",
                "agent_id": "agent-003",
                "position": {"x": 860, "y": 220},
                "data": {
                    "name": "Eligibility & Risk Check",
                    "type": "automatic",
                    "description": "AI-driven eligibility scoring and risk categorisation for FD applicant",
                    "properties": {"model": "llama-3.3-70b-versatile", "confidence_threshold": 0.85},
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "kyc_decisions",
                                "value_type": "data_model",
                                "value": "{{KYCVerification.kyc_decisions}}",
                                "description": "KYC decisions count feeds into risk scoring"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "processed",
                                "value_type": "data_model",
                                "value": "{{RiskProfile.records_assessed}}",
                                "description": "Write assessed record count to RiskProfile"
                            },
                            {
                                "name": "errors",
                                "value_type": "data_model",
                                "value": "{{RiskProfile.assessment_errors}}",
                                "description": "Write risk assessment errors to RiskProfile"
                            }
                        ]
                    }
                }
            },

            # ── Node 5: Configure FD Terms ─────────────────────────
            {
                "id": "fd-n5",
                "node_kind": "agent",
                "agent_id": "agent-014",
                "position": {"x": 1120, "y": 220},
                "data": {
                    "name": "Configure FD Terms",
                    "type": "orchestrator",
                    "description": "Decompose FD term configuration: tenor selection, interest rate lookup, nomination, auto-renewal",
                    "properties": {
                        "decomposition_strategy": "llm",
                        "merge_strategy": "reduce",
                        "max_sub_agents": 4
                    },
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "risk_records",
                                "value_type": "data_model",
                                "value": "{{RiskProfile.records_assessed}}",
                                "description": "Eligible applicant count from risk assessment"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "sub_tasks_created",
                                "value_type": "data_model",
                                "value": "{{FDConfiguration.sub_tasks_created}}",
                                "description": "Number of FD configuration sub-tasks dispatched"
                            },
                            {
                                "name": "sub_tasks_completed",
                                "value_type": "data_model",
                                "value": "{{FDConfiguration.sub_tasks_completed}}",
                                "description": "Number of FD configuration sub-tasks completed"
                            }
                        ]
                    }
                }
            },

            # ── Node 6: Calculate Maturity Returns ─────────────────
            {
                "id": "fd-n6",
                "node_kind": "agent",
                "agent_id": "agent-002",
                "position": {"x": 1380, "y": 220},
                "data": {
                    "name": "Calculate Maturity Returns",
                    "type": "automatic",
                    "description": "Compute maturity amount, interest earned, and TDS applicability for each FD",
                    "properties": {"validation_schema": {}, "error_threshold": 0.01},
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "fd_tasks_done",
                                "value_type": "data_model",
                                "value": "{{FDConfiguration.sub_tasks_completed}}",
                                "description": "Completed FD configuration count to compute returns for"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "processed",
                                "value_type": "data_model",
                                "value": "{{MaturityDetails.records_computed}}",
                                "description": "Write maturity computation count to MaturityDetails"
                            },
                            {
                                "name": "errors",
                                "value_type": "data_model",
                                "value": "{{MaturityDetails.computation_errors}}",
                                "description": "Write computation errors to MaturityDetails"
                            }
                        ]
                    }
                }
            },

            # ── Node 7: Compliance Audit ────────────────────────────
            {
                "id": "fd-n7",
                "node_kind": "agent",
                "agent_id": "agent-009",
                "position": {"x": 1640, "y": 220},
                "data": {
                    "name": "Compliance Audit",
                    "type": "role_based",
                    "description": "Regulatory compliance check: RBI FD guidelines, FEMA, tax obligations",
                    "properties": {"roles": ["compliance_officer", "risk_manager"], "require_all": True},
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "maturity_records",
                                "value_type": "data_model",
                                "value": "{{MaturityDetails.records_computed}}",
                                "description": "Records with computed maturity pending compliance sign-off"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "decisions",
                                "value_type": "data_model",
                                "value": "{{ComplianceRecord.compliance_decisions}}",
                                "description": "Write compliance decision count to ComplianceRecord"
                            },
                            {
                                "name": "escalated",
                                "value_type": "data_model",
                                "value": "{{ComplianceRecord.compliance_escalated}}",
                                "description": "Write escalated compliance cases"
                            }
                        ]
                    }
                }
            },

            # ── Node 8: Create FD Account ──────────────────────────
            {
                "id": "fd-n8",
                "node_kind": "agent",
                "agent_id": "agent-006",
                "position": {"x": 1900, "y": 220},
                "data": {
                    "name": "Create FD Account",
                    "type": "automatic",
                    "description": "Persist FD account in core banking, generate account number, issue e-receipt",
                    "properties": {"operation": "upsert", "batch_size": 100},
                    "invoke": {
                        "input_parameters": [
                            {
                                "name": "compliance_decisions",
                                "value_type": "data_model",
                                "value": "{{ComplianceRecord.compliance_decisions}}",
                                "description": "Compliance-cleared records ready for account creation"
                            }
                        ],
                        "output_parameters": [
                            {
                                "name": "processed",
                                "value_type": "data_model",
                                "value": "{{AccountSetup.accounts_processed}}",
                                "description": "Write created FD account count to AccountSetup"
                            },
                            {
                                "name": "errors",
                                "value_type": "data_model",
                                "value": "{{AccountSetup.setup_errors}}",
                                "description": "Write account creation errors to AccountSetup"
                            }
                        ]
                    }
                }
            },

            # ── Node 9: Workflow End ───────────────────────────────
            {
                "id": "fd-n9",
                "node_kind": "agent",
                "agent_id": "agent-end",
                "position": {"x": 2160, "y": 220},
                "data": {
                    "name": "Workflow End",
                    "type": "end",
                    "description": "Finalise FD opening process and archive data model instance",
                    "properties": {
                        "notify_on_complete": True,
                        "summary": "Fixed Deposit opening process completed."
                    },
                    "invoke": {
                        "input_parameters": [],
                        "output_parameters": []
                    }
                }
            }
        ],
        "edges": [
            {"id": "fd-e1", "source": "fd-n1", "target": "fd-n2", "label": "start"},
            {"id": "fd-e2", "source": "fd-n2", "target": "fd-n3", "label": "applicant data"},
            {"id": "fd-e3", "source": "fd-n3", "target": "fd-n4", "label": "kyc cleared"},
            {"id": "fd-e4", "source": "fd-n4", "target": "fd-n5", "label": "risk profile"},
            {"id": "fd-e5", "source": "fd-n5", "target": "fd-n6", "label": "fd terms set"},
            {"id": "fd-e6", "source": "fd-n6", "target": "fd-n7", "label": "maturity computed"},
            {"id": "fd-e7", "source": "fd-n7", "target": "fd-n8", "label": "compliance approved"},
            {"id": "fd-e8", "source": "fd-n8", "target": "fd-n9", "label": "accounts created"}
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Print helpers
# ─────────────────────────────────────────────────────────────────────────────

STEP_ENTITY_MAP = {
    "Collect Applicant Details":      "ApplicationInfo",
    "KYC & Document Verification":    "KYCVerification",
    "Eligibility & Risk Check":       "RiskProfile",
    "Configure FD Terms":             "FDConfiguration",
    "Calculate Maturity Returns":      "MaturityDetails",
    "Compliance Audit":               "ComplianceRecord",
    "Create FD Account":              "AccountSetup",
}


def print_section(title: str):
    print(f"\n{C('bold')}{C('cyan')}{'=' * 68}{R}")
    print(f"{C('bold')}{C('cyan')}  {title}{R}")
    print(f"{C('bold')}{C('cyan')}{'=' * 68}{R}")


def print_step_result(i: int, step: dict, dm_state: dict):
    name   = step.get("agent_name", "Unknown")
    status = step.get("status", "?")
    dur    = step.get("duration_ms", 0)
    inv_in  = step.get("invoke_inputs", {})
    inv_out = step.get("invoke_outputs", {})

    status_color = C("green") if status == "completed" else C("red") if status == "failed" else C("yellow")
    print(f"\n  {C('bold')}Step {i+1}: {name}{R}  {status_color}[{status}]{R}  {C('yellow')}{dur}ms{R}")

    if inv_in:
        print(f"    {C('violet')}[IN] Inputs Resolved:{R}")
        for k, v in inv_in.items():
            print(f"      {k} = {C('cyan')}{repr(v)}{R}")

    if inv_out:
        print(f"    {C('violet')}[OUT] Outputs Captured:{R}")
        for k, v in inv_out.items():
            print(f"      {k} = {C('green')}{repr(v)}{R}")

    # Show the relevant data model entity for this step
    entity = STEP_ENTITY_MAP.get(name)
    if entity and entity in dm_state:
        fields = dm_state[entity]
        print(f"    {C('bold')}Data Model · {entity}:{R}")
        for fname, fval in fields.items():
            marker = "+" if fval not in (0, None, "") else "-"
            color  = C("green") if fval not in (0, None, "") else C("yellow")
            print(f"      {color}{marker} {fname} = {fval}{R}")


def print_final_dm(dm: dict):
    print_section("FINAL DATA MODEL INSTANCE — Fixed Deposit")
    for entity, fields in dm.items():
        print(f"\n  {C('bold')}{entity}{R}")
        for fname, fval in fields.items():
            changed = fval not in (0, None, "")
            marker  = "+" if changed else "-"
            color   = C("green") if changed else C("yellow")
            print(f"    {color}{marker} {fname:<30} = {fval}{R}")


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print_section("Fixed Deposit Workflow — Seed & Test")

    # ── Step 1: Create data model ──────────────────────────────────────────
    print(f"\n{C('bold')}[1] Creating data model…{R}")
    dm = _req("POST", "/data-models", DATA_MODEL_PAYLOAD)
    dm_id = dm["id"]
    print(f"  OK Data model created: {C('green')}{dm['name']}{R}  id={dm_id}")
    print(f"    Entities: {[e['name'] for e in dm['entities']]}")

    # ── Step 2: Create workflow ────────────────────────────────────────────
    print(f"\n{C('bold')}[2] Creating workflow…{R}")
    wf_payload = build_workflow_payload()
    wf = _req("POST", "/workflows", wf_payload)
    wf_id = wf["id"]
    print(f"  OK Workflow created: {C('green')}{wf['name']}{R}  id={wf_id}")
    print(f"    Nodes: {[n['data']['name'] for n in wf['nodes']]}")

    # ── Step 3: Create association ─────────────────────────────────────────
    print(f"\n{C('bold')}[3] Linking workflow ↔ data model…{R}")
    assoc = _req("POST", "/associations", {
        "workflow_id":     wf_id,
        "data_model_id":   dm_id,
        "project":         "RetailBanking",
        "environment":     "uat",
        "global_context":  {
            "bank_code":       "BANK_IN",
            "currency":        "INR",
            "min_fd_amount":   10000,
            "max_tenor_months": 120,
            "default_tenor":   12
        },
        "input_mappings":  [],
        "default_values":  {},
        "validation_rules": [],
        "activity_bindings": []
    })
    print(f"  OK Association created: id={assoc['id']}")

    # ── Step 4: Run workflow ───────────────────────────────────────────────
    print(f"\n{C('bold')}[4] Running workflow execution…{R}")
    result = _req("POST", f"/execution/{wf_id}/run", None)
    run_id     = result["id"]
    run_status = result["status"]
    total_ms   = result.get("total_duration_ms", 0)
    dm_final   = result.get("data_model_instance", {})
    steps      = result.get("steps", [])

    status_color = C("green") if run_status == "completed" else C("red")
    print(f"  OK Run id={run_id}  status={status_color}{run_status}{R}  duration={C('yellow')}{total_ms}ms{R}")

    # ── Step 5: Print step-by-step data model evolution ───────────────────
    print_section("STEP-BY-STEP DATA MODEL EVOLUTION")

    # Build authoritative output-param map:
    #   (agent_name, param_name) -> (entity_name, field_name)
    # Parsed directly from the workflow's invoke output_parameters.
    import re as _re
    output_map: dict = {}  # (agent_name, param_name) -> (entity, field)
    for node in wf_payload["nodes"]:
        aname = node["data"]["name"]
        for op in node["data"].get("invoke", {}).get("output_parameters", []):
            m = _re.match(r"\{\{([^.}]+)\.([^}]+)\}\}", op.get("value", "").strip())
            if m:
                output_map[(aname, op["name"])] = (m.group(1), m.group(2))

    # Initialise DM state from model defaults
    dm_state = {
        entity_data["name"]: {f["name"]: f["default_value"] for f in entity_data["fields"]}
        for entity_data in DATA_MODEL_PAYLOAD["entities"]
    }

    for i, step in enumerate(steps):
        name = step.get("agent_name", "")
        # Apply this step's captured outputs to the simulated DM state
        for param_name, captured_val in step.get("invoke_outputs", {}).items():
            target = output_map.get((name, param_name))
            if target:
                entity, field = target
                if entity in dm_state and field in dm_state[entity]:
                    dm_state[entity][field] = captured_val

        print_step_result(i, step, dm_state)

    # ── Step 6: Final data model from server ──────────────────────────────
    print_final_dm(dm_final)

    # ── Summary ───────────────────────────────────────────────────────────
    print_section("SUMMARY")
    entities_populated = sum(
        1 for fields in dm_final.values()
        if any(v not in (0, None, "") for v in fields.values())
    )
    total_fields = sum(len(f) for f in dm_final.values())
    written_fields = sum(
        1 for fields in dm_final.values()
        for v in fields.values() if v not in (0, None, "")
    )
    print(f"\n  Workflow        : {wf['name']}")
    print(f"  Workflow ID     : {wf_id}")
    print(f"  Data Model ID   : {dm_id}")
    print(f"  Run ID          : {run_id}")
    print(f"  Run Status      : {status_color}{run_status}{R}")
    print(f"  Total Duration  : {total_ms}ms")
    print(f"  Steps executed  : {len([s for s in steps if s['status'] != 'skipped'])} / {len(steps)}")
    print(f"  DM entities     : {entities_populated}/{len(dm_final)} populated")
    print(f"  DM fields       : {written_fields}/{total_fields} written\n")
    print(f"  {C('green')}Test URLs:{R}")
    print(f"    Workflow : {BASE}/workflows/{wf_id}")
    print(f"    Run      : {BASE}/execution/{run_id}")
    print(f"    DM       : {BASE}/data-models/{dm_id}\n")


if __name__ == "__main__":
    main()
