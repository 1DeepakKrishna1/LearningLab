import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from "@xyflow/react";
import { Box, Button, Stack, TextField, Snackbar, Alert, Chip } from "@mui/material";
import { Save, Play, CheckCircle } from "lucide-react";
import NodePalette from "../components/NodePalette";
import NodeConfigPanel from "../components/NodeConfigPanel";
import FlowNode from "../components/FlowNode";
import { Api } from "../api/client";

let idSeq = 1;
const nextId = () => `n${Date.now()}_${idSeq++}`;

function Builder() {
  const { id } = useParams();
  const navigate = useNavigate();
  // All domain node types render through one wrapper component.
  const nodeTypes = useMemo(() => ({ claw: FlowNode }), []);
  const wrapper = useRef<HTMLDivElement>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [rfi, setRfi] = useState<ReactFlowInstance | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const [name, setName] = useState("Untitled Workflow");
  const [toast, setToast] = useState<{ msg: string; sev: "success" | "error" } | null>(null);

  // Load existing workflow.
  useEffect(() => {
    if (!id || id === "new") return;
    Api.workflow(id).then((wf) => {
      setName(wf.name);
      setNodes(wf.nodes.map((n) => ({
        id: n.id, type: "claw", position: n.position,
        data: { ...n.data, cfType: n.type },
      })) as any);
      setEdges(wf.edges.map((e) => ({
        id: e.id, source: e.source, target: e.target,
        sourceHandle: e.sourceHandle ?? undefined, label: e.sourceHandle ?? undefined,
      })) as any);
    });
  }, [id]);

  const onConnect = useCallback(
    (c: Connection) => setEdges((eds) => addEdge({ ...c, label: c.sourceHandle ?? undefined }, eds)),
    [setEdges]
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData("application/clawflow-node");
      if (!raw || !rfi) return;
      const { type, label } = JSON.parse(raw);
      const position = rfi.screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const newNode: Node = {
        id: nextId(), type: "claw", position,
        data: { label, config: {}, cfType: type },
      };
      setNodes((nds) => nds.concat(newNode));
    },
    [rfi, setNodes]
  );

  const updateNodeData = (nodeId: string, data: any) => {
    setNodes((nds) => nds.map((n) => (n.id === nodeId ? { ...n, data } : n)));
    setSelected((s) => (s && s.id === nodeId ? { ...s, data } : s));
  };

  const deleteNode = (nodeId: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelected(null);
  };

  const serialize = () => ({
    name,
    nodes: nodes.map((n) => ({
      id: n.id, type: ((n.data as any).cfType as string) || (n.type as string),
      position: n.position,
      data: { label: (n.data as any).label || "", config: (n.data as any).config || {},
        agent_id: (n.data as any).agent_id ?? null },
    })),
    edges: edges.map((e) => ({
      id: e.id, source: e.source, target: e.target,
      sourceHandle: (e.sourceHandle as string) ?? null,
    })),
  });

  const save = async () => {
    try {
      const payload = serialize();
      if (!id || id === "new") {
        const created = await Api.createWorkflow(payload as any);
        navigate(`/workflows/${created.id}`, { replace: true });
      } else {
        await Api.updateWorkflow(id, payload as any);
      }
      setToast({ msg: "Workflow saved", sev: "success" });
    } catch {
      setToast({ msg: "Save failed", sev: "error" });
    }
  };

  const validate = async () => {
    if (!id || id === "new") { await save(); return; }
    const res = await Api.validateWorkflow(id);
    setToast({ msg: res.valid ? "Valid ✓" : `Invalid: ${res.errors.join(", ")}`,
      sev: res.valid ? "success" : "error" });
  };

  const run = async () => {
    if (!id || id === "new") { await save(); return; }
    const res = await Api.runWorkflow(id);
    setToast({ msg: `Started execution ${res.execution_id.slice(0, 8)}`, sev: "success" });
    navigate("/executions");
  };

  return (
    <Box sx={{ height: "calc(100vh - 112px)", display: "flex", flexDirection: "column" }}>
      <Stack direction="row" spacing={2} sx={{ mb: 1, alignItems: "center" }}>
        <TextField size="small" value={name} onChange={(e) => setName(e.target.value)}
          sx={{ width: 300 }} />
        <Button variant="outlined" startIcon={<CheckCircle size={16} />} onClick={validate}>
          Validate
        </Button>
        <Button variant="outlined" startIcon={<Save size={16} />} onClick={save}>Save</Button>
        <Button variant="contained" startIcon={<Play size={16} />} onClick={run}>Run</Button>
        <Chip size="small" label={`${nodes.length} nodes`} />
      </Stack>

      <Box sx={{ flexGrow: 1, display: "flex", border: "1px solid #e2e8f0", borderRadius: 2,
        overflow: "hidden", bgcolor: "#fff" }}>
        <NodePalette />
        <div ref={wrapper} style={{ flexGrow: 1 }}
          onDrop={onDrop} onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setRfi}
            onNodeClick={(_, n) => setSelected(n)}
            onPaneClick={() => setSelected(null)}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>
        <NodeConfigPanel node={selected} onChange={updateNodeData} onDelete={deleteNode} />
      </Box>

      <Snackbar open={!!toast} autoHideDuration={4000} onClose={() => setToast(null)}>
        {toast ? <Alert severity={toast.sev}>{toast.msg}</Alert> : undefined}
      </Snackbar>
    </Box>
  );
}

export default function WorkflowBuilder() {
  return (
    <ReactFlowProvider>
      <Builder />
    </ReactFlowProvider>
  );
}
