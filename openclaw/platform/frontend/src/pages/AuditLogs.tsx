import { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Chip, Typography, Table, TableBody, TableCell,
  TableHead, TableRow,
} from "@mui/material";
import { Api } from "../api/client";
import type { AuditEntry } from "../api/types";

export default function AuditLogs() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);

  useEffect(() => {
    const load = () => Api.audit().then(setEntries).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>Audit Logs</Typography>
      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Actor</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Result</TableCell>
                <TableCell>Detail</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {entries.map((e) => (
                <TableRow key={e.id} hover>
                  <TableCell>{e.timestamp.slice(0, 19).replace("T", " ")}</TableCell>
                  <TableCell><Chip size="small" label={e.actor} /></TableCell>
                  <TableCell>{e.action}</TableCell>
                  <TableCell>
                    <Chip size="small" label={e.result}
                      color={e.result === "error" ? "error" : e.result === "success" ? "success" : "default"} />
                  </TableCell>
                  <TableCell sx={{ fontSize: 11, fontFamily: "monospace", maxWidth: 360, overflow: "hidden" }}>
                    {JSON.stringify(e.detail)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {entries.length === 0 && <Typography color="text.secondary" sx={{ p: 2 }}>No audit entries.</Typography>}
        </CardContent>
      </Card>
    </Box>
  );
}
