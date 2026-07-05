import { Handle, Position, NodeProps } from "@xyflow/react";

const GROUP_COLOR: Record<string, string> = {
  trigger: "#16A34A",
  agent: "#7C3AED",
  logic: "#D97706",
  tool: "#6366F1",
  action: "#0EA5E9",
};

// Conditional node types expose multiple labelled source handles.
const BRANCHES: Record<string, string[]> = {
  "logic.if_else": ["true", "false"],
  "logic.approval": ["approved", "rejected", "changes"],
};

export default function FlowNode({ type, data, selected }: NodeProps) {
  // The domain node type is stored in data.cfType; `type` is always our wrapper.
  const cfType = ((data as any)?.cfType as string) || (type as string);
  const group = cfType.split(".")[0];
  const color = GROUP_COLOR[group] ?? "#64748B";
  const label = (data as any)?.label || cfType;
  const branches = BRANCHES[cfType];

  return (
    <div className="cf-node" style={{ outline: selected ? `2px solid ${color}` : "none" }}>
      <Handle type="target" position={Position.Left} />
      <div className="cf-node__header" style={{ background: color }}>
        <span>{label}</span>
      </div>
      <div className="cf-node__body">
        <code style={{ fontSize: 11, color: "#94a3b8" }}>{cfType}</code>
      </div>
      {branches ? (
        branches.map((b, i) => (
          <Handle
            key={b}
            id={b}
            type="source"
            position={Position.Right}
            style={{ top: 30 + i * 16 }}
            title={b}
          />
        ))
      ) : (
        <Handle type="source" position={Position.Right} />
      )}
    </div>
  );
}
