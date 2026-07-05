"""Unit/integration tests for the workflow engine (no LLM required)."""
import asyncio

from app.domain.enums import ExecutionStatus
from app.domain.workflow import WorkflowCreate, WorkflowEdge, WorkflowNode


async def _settle(container, execution_id, terminal_only=False, tries=120):
    for _ in range(tries):
        ex = await container.execution_service.get(execution_id)
        if ex.status.is_terminal:
            return ex
        if not terminal_only and ex.status == ExecutionStatus.WAITING_APPROVAL:
            return ex
        await asyncio.sleep(0.02)
    return await container.execution_service.get(execution_id)


async def test_conditional_branch_and_skip(container, tmp_path):
    report = tmp_path / "r.md"
    nodes = [
        WorkflowNode(id="n1", type="trigger.manual", data={"config": {}}),
        WorkflowNode(id="n2", type="logic.if_else",
                     data={"config": {"left": "{{ trigger.payload.amount }}",
                                      "operator": ">", "right": 100}}),
        WorkflowNode(id="n3", type="action.generate_report",
                     data={"config": {"title": "Big", "path": str(report),
                                      "sections": [{"heading": "amt",
                                                    "body": "{{ trigger.payload.amount }}"}]}}),
        WorkflowNode(id="n4", type="action.generate_report",
                     data={"config": {"title": "Small"}}),
    ]
    edges = [WorkflowEdge(source="n1", target="n2"),
             WorkflowEdge(source="n2", target="n3", sourceHandle="true"),
             WorkflowEdge(source="n2", target="n4", sourceHandle="false")]
    wf = await container.workflow_service.create(
        WorkflowCreate(name="cond", nodes=nodes, edges=edges))

    ex = await container.execution_service.start(wf.id, payload={"amount": 250})
    ex = await _settle(container, ex.id, terminal_only=True)

    assert ex.status == ExecutionStatus.COMPLETED
    statuses = {r.node_id: r.status.value for r in ex.node_runs}
    assert statuses["n3"] == "completed"
    assert statuses["n4"] == "skipped"
    assert report.exists() and "250" in report.read_text()


async def test_approval_suspends_and_resumes(container):
    nodes = [
        WorkflowNode(id="n1", type="trigger.manual", data={"config": {}}),
        WorkflowNode(id="n2", type="logic.approval",
                     data={"config": {"channel": "ui", "title": "Approve me"}}),
        WorkflowNode(id="n3", type="action.generate_report",
                     data={"config": {"title": "Done"}}),
    ]
    edges = [WorkflowEdge(source="n1", target="n2"),
             WorkflowEdge(source="n2", target="n3", sourceHandle="approved")]
    wf = await container.workflow_service.create(
        WorkflowCreate(name="appr", nodes=nodes, edges=edges))

    ex = await container.execution_service.start(wf.id)
    ex = await _settle(container, ex.id)
    assert ex.status == ExecutionStatus.WAITING_APPROVAL

    approvals = await container.approval_service.list(status="pending")
    assert len(approvals) == 1

    from app.domain.approval import ApprovalDecision
    from app.domain.enums import ApprovalStatus
    await container.approval_service.decide(
        ApprovalDecision(approval_id=approvals[0].id, decision=ApprovalStatus.APPROVED),
        decided_by="tester")

    ex = await _settle(container, ex.id, terminal_only=True)
    assert ex.status == ExecutionStatus.COMPLETED
    statuses = {r.node_id: r.status.value for r in ex.node_runs}
    assert statuses["n3"] == "completed"


async def test_tool_node_present(container):
    # excel create_excel_file is dependency-light and present in the library.
    assert container.tool_service.get("excel_tools.create_excel_file") is not None
