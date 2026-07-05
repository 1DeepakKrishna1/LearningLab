import pytest
from pathlib import Path

def test_loader_and_execution(tmp_path):
    # use the real data files
    base = Path(__file__).parent.parent
    loader_path = base
    from engine.loader import DataLoader
    from engine.executor import WorkflowExecutor

    loader = DataLoader(loader_path / "dummy_data.json", loader_path / "myworkflow.json")

    # ensure workflows loaded
    assert "Customer Onboarding (Myflow)" in loader.workflows

    executor = WorkflowExecutor(loader)
    result = executor.execute("Customer Onboarding (Myflow)", {"example": 123})
    assert "state" in result
    assert result["state"]["workflow_name"] == "Customer Onboarding (Myflow)"
    # confirm log entries exist
    assert isinstance(result["log"], list)
    assert len(result["log"]) > 0

    # state should include tool_results and node_states map
    assert "tool_results" in result["state"]
    assert "node_states" in result["state"]

    # running a non-existent workflow raises KeyError
    with pytest.raises(KeyError):
        executor.execute("not real", {})

    # strategy switch: set to langgraph (even if not installed) should not crash
    import os
    os.environ["WORKFLOW_EXECUTION_STRATEGY"] = "langgraph"
    executor2 = WorkflowExecutor(loader)
    # if langgraph isn't available the executor should fall back to topological
    r2 = executor2.execute("Customer Onboarding (Myflow)", {"example": 456})
    assert r2["state"]["workflow_name"] == "Customer Onboarding (Myflow)"
