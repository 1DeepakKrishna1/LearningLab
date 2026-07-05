const STATUS_COLORS = {
  draft: "gray",
  in_progress: "blue",
  eligible: "green",
  ineligible: "red",
  evaluated: "purple",
  ranked: "amber",
  allocated: "green",
  enrolled: "green",
  rejected: "red",
  withdrawn: "gray",
  pending: "gray",
  completed: "green",
  skipped: "gray",
  verified: "green",
  paid: "green",
  active: "green",
  closed: "gray",
  allotted: "blue",
  accepted: "green",
  declined: "red",
};

export function Badge({ value, color }) {
  const c = color || STATUS_COLORS[value] || "gray";
  return <span className={`badge ${c}`}>{String(value).replace(/_/g, " ")}</span>;
}

export function Stepper({ stages }) {
  return (
    <div className="stepper">
      {stages.map((s) => (
        <div
          key={s.key}
          className={`step ${s.status === "completed" ? "completed" : ""} ${
            s.is_current ? "current" : ""
          }`}
          title={`${s.name} — ${s.status}`}
        >
          {s.ai_enabled && <span className="ai-dot" title="AI enabled" />}
          {s.name}
        </div>
      ))}
    </div>
  );
}

export function Stat({ num, label }) {
  return (
    <div className="card stat">
      <div className="num">{num}</div>
      <div className="lbl">{label}</div>
    </div>
  );
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
