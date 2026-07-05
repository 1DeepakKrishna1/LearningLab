# Workflow Execution Engine

This repository implements a Python-based workflow execution engine.
It uses data defined in `dummy_data.json` (tools/agents definitions) and
`myworkflow.json` (workflows with nodes/edges) to run dummy workflows.

## Features

- Agents and Tools exposed as Python classes
- Execution engine supports topological order or `langgraph` strategy
  configured via `.env` (``WORKFLOW_EXECUTION_STRATEGY``)
- State tracking and logging for every step
- FastAPI endpoint to trigger workflows via HTTP
- Dummy implementations generated from JSON definitions

## Getting Started

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. Run the FastAPI app:
   ```bash
   uvicorn api.main:app --reload
   ```
   The `/execute` endpoint accepts POST requests with JSON
   ``{ "workflow_name": "Customer Onboarding (Myflow)",
   "start_properties": {...} }``

3. Execute tests:
   ```bash
   pytest
   ```

## Extensibility

- Add new agents/tools by updating `dummy_data.json`.
- `engine/factories.py` will provide easy access to class instances.
- Workflow definitions reside in `myworkflow.json` but can be loaded from
  elsewhere by adapting `loader.DataLoader`.

---
Generated according to specification in `spec.txt`.
