import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout.jsx";
import { Badge, Stat, Empty } from "../../components/ui.jsx";
import api from "../../api/client.js";

export default function ProductAdminHome() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/admin/overview").then((r) => setData(r.data));
  }, []);

  return (
    <Layout title="Systems Overview">
      <div className="grid cols-3">
        <Stat num={data?.total_systems ?? "…"} label="Configured Systems" />
        <Stat num={data?.systems?.reduce((a, s) => a + s.applications, 0) ?? "…"} label="Total Applications" />
        <Stat num={data?.systems?.filter((s) => s.status === "active").length ?? "…"} label="Active Systems" />
      </div>

      <div className="card">
        <div className="spread">
          <h3>All Systems</h3>
          <Link to="/product/systems/new"><button className="btn-sm">+ Create System</button></Link>
        </div>
        {data && data.systems.length === 0 && <Empty>No systems yet. Create one to begin.</Empty>}
        {data && data.systems.length > 0 && (
          <table>
            <thead>
              <tr><th>Name</th><th>Domain</th><th>Status</th><th>Applications</th><th>Members</th><th></th></tr>
            </thead>
            <tbody>
              {data.systems.map((s) => (
                <tr key={s.id}>
                  <td><strong>{s.name}</strong><br /><span className="muted">{s.key}</span></td>
                  <td>{s.domain.replace(/_/g, " ")}</td>
                  <td><Badge value={s.status} /></td>
                  <td>{s.applications}</td>
                  <td>{s.members}</td>
                  <td><Link to={`/product/systems/${s.id}`}>Configure →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
