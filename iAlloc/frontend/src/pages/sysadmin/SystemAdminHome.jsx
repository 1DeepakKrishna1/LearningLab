import { useEffect, useState } from "react";
import Layout from "../../components/Layout.jsx";
import StageConfigEditor from "../../components/StageConfigEditor.jsx";
import { Badge, Empty } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

export default function SystemAdminHome() {
  const { user } = useAuth();
  const [system, setSystem] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!user.system_id) return;
    api
      .get(`/systems/${user.system_id}/admin/config`)
      .then((r) => setSystem(r.data))
      .catch((e) => setErr(apiError(e)));
  }, [user.system_id]);

  if (!user.system_id)
    return (
      <Layout title="Configure System">
        <Empty>You are not bound to a system. Use the Product console.</Empty>
      </Layout>
    );

  return (
    <Layout title="Configure System">
      {err && <div className="error">{err}</div>}
      {system && (
        <div className="card">
          <div className="spread">
            <div>
              <h3 style={{ marginBottom: 4 }}>{system.name}</h3>
              <Badge value={system.domain} color="purple" /> <Badge value={system.status} />
            </div>
          </div>
          <p className="muted">{system.description}</p>
        </div>
      )}
      <p className="muted">
        Enable/disable each lifecycle stage and turn on Groq AI assistance per stage.
        Stakeholders see the AI assistant only on stages where you enable it.
      </p>
      <StageConfigEditor systemId={Number(user.system_id)} />
    </Layout>
  );
}
