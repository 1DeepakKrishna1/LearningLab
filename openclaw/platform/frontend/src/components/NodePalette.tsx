import { useEffect, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  TextField,
  Typography,
} from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { Api } from "../api/client";
import type { NodeCatalog } from "../api/types";

// A palette entry is draggable; the workflow canvas reads the dataTransfer on drop.
function PaletteItem({ type, label, color }: { type: string; label: string; color?: string }) {
  return (
    <Box
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("application/clawflow-node", JSON.stringify({ type, label }));
        e.dataTransfer.effectAllowed = "move";
      }}
      sx={{
        px: 1.2, py: 0.8, mb: 0.6, borderRadius: 1, cursor: "grab",
        border: "1px solid #e2e8f0", bgcolor: "#fff", fontSize: 13,
        borderLeft: `4px solid ${color || "#6366F1"}`,
        "&:hover": { bgcolor: "#f8fafc" },
      }}
    >
      {label}
    </Box>
  );
}

export default function NodePalette() {
  const [catalog, setCatalog] = useState<NodeCatalog | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    Api.nodeCatalog().then(setCatalog).catch(() => {});
  }, []);

  if (!catalog) return <Typography sx={{ p: 2 }}>Loading palette…</Typography>;
  const q = filter.toLowerCase();

  return (
    <Box sx={{ width: 280, borderRight: "1px solid #e2e8f0", overflow: "auto", bgcolor: "#fbfbfd" }}>
      <Box sx={{ p: 1.5 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>Node Palette</Typography>
        <TextField size="small" fullWidth placeholder="Search nodes…" value={filter}
          onChange={(e) => setFilter(e.target.value)} />
      </Box>

      {Object.entries(catalog.static).map(([group, items]) => {
        const visible = items.filter((i) => i.label.toLowerCase().includes(q) || i.type.includes(q));
        if (!visible.length) return null;
        return (
          <Accordion key={group} disableGutters defaultExpanded={group === "trigger"}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography sx={{ textTransform: "capitalize", fontWeight: 600 }}>{group}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {visible.map((i) => <PaletteItem key={i.type} type={i.type} label={i.label} />)}
            </AccordionDetails>
          </Accordion>
        );
      })}

      <Accordion disableGutters>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography sx={{ fontWeight: 600 }}>
            Tools <Chip size="small" label={Object.values(catalog.tools).flat().length} sx={{ ml: 1 }} />
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          {Object.entries(catalog.tools).map(([cat, items]) => {
            const visible = items.filter((i) => i.label.toLowerCase().includes(q) || i.type.includes(q));
            if (!visible.length) return null;
            return (
              <Box key={cat} sx={{ mb: 1 }}>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>{cat}</Typography>
                {visible.map((i) => (
                  <PaletteItem key={i.type} type={i.type} label={i.label} color={i.color} />
                ))}
              </Box>
            );
          })}
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}
