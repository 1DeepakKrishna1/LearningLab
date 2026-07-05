import { useEffect, useState } from "react";
import { Box, Button, Card, CardContent, TextField, Typography, MenuItem, Snackbar, Alert } from "@mui/material";
import { Api } from "../api/client";

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => { Api.settings().then(setSettings).catch(() => {}); }, []);

  const save = async () => {
    await Api.updateSettings(settings);
    setSaved(true);
  };

  const set = (k: string, v: any) => setSettings({ ...settings, [k]: v });

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>Settings</Typography>
      <Card sx={{ maxWidth: 600 }}>
        <CardContent>
          <TextField select fullWidth label="Default LLM Provider" margin="normal"
            value={settings.default_llm_provider || "anthropic"}
            onChange={(e) => set("default_llm_provider", e.target.value)}>
            {["anthropic", "openai", "google", "ollama", "groq"].map((p) =>
              <MenuItem key={p} value={p}>{p}</MenuItem>)}
          </TextField>
          <TextField fullWidth label="Default LLM Model" margin="normal"
            value={settings.default_llm_model || ""}
            onChange={(e) => set("default_llm_model", e.target.value)} />
          <TextField select fullWidth label="Messaging Provider" margin="normal"
            value={settings.messaging_provider || "console"}
            onChange={(e) => set("messaging_provider", e.target.value)}>
            {["console", "meta", "twilio"].map((p) =>
              <MenuItem key={p} value={p}>{p}</MenuItem>)}
          </TextField>
          <TextField fullWidth type="number" label="Max Parallel Nodes" margin="normal"
            value={settings.max_parallel_nodes || 8}
            onChange={(e) => set("max_parallel_nodes", Number(e.target.value))} />
          <Button variant="contained" sx={{ mt: 2 }} onClick={save}>Save Settings</Button>
        </CardContent>
      </Card>
      <Snackbar open={saved} autoHideDuration={3000} onClose={() => setSaved(false)}>
        <Alert severity="success">Settings saved</Alert>
      </Snackbar>
    </Box>
  );
}
