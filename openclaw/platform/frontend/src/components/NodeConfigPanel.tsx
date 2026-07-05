import { useEffect, useState } from "react";
import {
  Box, TextField, Typography, MenuItem, Button, Divider, Alert,
} from "@mui/material";
import { Trash2 } from "lucide-react";
import { Api } from "../api/client";
import type { Agent } from "../api/types";
import type { Node } from "@xyflow/react";

interface Props {
  node: Node | null;
  onChange: (id: string, data: any) => void;
  onDelete: (id: string) => void;
}

export default function NodeConfigPanel({ node, onChange, onDelete }: Props) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [configText, setConfigText] = useState("{}");
  const [jsonError, setJsonError] = useState("");

  useEffect(() => {
    Api.agents().then(setAgents).catch(() => {});
  }, []);

  useEffect(() => {
    if (node) setConfigText(JSON.stringify((node.data as any)?.config ?? {}, null, 2));
  }, [node?.id]);

  if (!node) {
    return (
      <Box sx={{ width: 320, p: 2, borderLeft: "1px solid #e2e8f0", bgcolor: "#fbfbfd" }}>
        <Typography color="text.secondary">Select a node to configure it.</Typography>
      </Box>
    );
  }

  const data = node.data as any;
  const isAgent = (node.type as string).startsWith("agent.");

  const commitConfig = (text: string) => {
    setConfigText(text);
    try {
      const parsed = JSON.parse(text || "{}");
      setJsonError("");
      onChange(node.id, { ...data, config: parsed });
    } catch {
      setJsonError("Invalid JSON");
    }
  };

  return (
    <Box sx={{ width: 320, p: 2, borderLeft: "1px solid #e2e8f0", overflow: "auto", bgcolor: "#fbfbfd" }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Node Settings</Typography>
      <Typography variant="caption" color="text.secondary">{node.type as string}</Typography>

      <TextField fullWidth size="small" label="Label" sx={{ mt: 2 }} value={data.label || ""}
        onChange={(e) => onChange(node.id, { ...data, label: e.target.value })} />

      {isAgent && (
        <TextField select fullWidth size="small" label="Agent" sx={{ mt: 2 }}
          value={data.agent_id || ""}
          onChange={(e) => onChange(node.id, { ...data, agent_id: e.target.value })}>
          <MenuItem value="">(ephemeral)</MenuItem>
          {agents.map((a) => (
            <MenuItem key={a.agent_id} value={a.agent_id}>{a.name} ({a.role})</MenuItem>
          ))}
        </TextField>
      )}

      <Typography variant="caption" sx={{ mt: 2, display: "block" }}>Config (JSON)</Typography>
      <TextField fullWidth multiline minRows={8} size="small" value={configText}
        onChange={(e) => commitConfig(e.target.value)}
        sx={{ fontFamily: "monospace", "& textarea": { fontFamily: "monospace", fontSize: 12 } }} />
      {jsonError && <Alert severity="error" sx={{ mt: 1 }}>{jsonError}</Alert>}

      <Divider sx={{ my: 2 }} />
      <Button color="error" startIcon={<Trash2 size={16} />} onClick={() => onDelete(node.id)}>
        Delete node
      </Button>
    </Box>
  );
}
