import './ResultRenderer.css'

interface Props {
  patternId: number
  result: Record<string, unknown>
}

/** Render a highlighted code/text block */
function CodeBlock({ code }: { code: string }) {
  return <pre className="rr-code">{code}</pre>
}

/** Render a key-value badge row */
function Badge({ label, value }: { label: string; value: string }) {
  return (
    <span className="rr-badge">
      <span className="rr-badge-label">{label}</span>
      <span className="rr-badge-value">{value}</span>
    </span>
  )
}

/** Section with a title */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rr-section">
      <div className="rr-section-title">{title}</div>
      <div className="rr-section-body">{children}</div>
    </div>
  )
}

function str(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  return JSON.stringify(v, null, 2)
}

// ─── Per-pattern renderers ────────────────────────────────────────────────

function PromptChaining({ r }: { r: Record<string, unknown> }) {
  return (
    <>
      <Section title="Headline">
        <p className="rr-headline">{str(r.headline)}</p>
      </Section>
      <Section title="Edited Article">
        <p className="rr-prose">{str(r.edited)}</p>
      </Section>
      <Section title="Outline">
        <p className="rr-prose rr-secondary">{str(r.outline)}</p>
      </Section>
    </>
  )
}

function Routing({ r }: { r: Record<string, unknown> }) {
  return (
    <>
      <Badge label="Route" value={str(r.route)} />
      <Section title="Response">
        <p className="rr-prose">{str(r.response)}</p>
      </Section>
    </>
  )
}

function Parallelization({ r }: { r: Record<string, unknown> }) {
  const perspectives = (r.perspectives as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <Section title="Synthesis">
        <p className="rr-prose">{str(r.synthesis)}</p>
      </Section>
      {perspectives.map((p, i) => (
        <Section key={i} title={`${str(p.label ?? p.perspective)} Perspective`}>
          <p className="rr-prose rr-secondary">{str(p.content ?? p.text ?? p.output)}</p>
        </Section>
      ))}
      {r.elapsed_seconds != null && (
        <Badge label="Elapsed" value={`${(r.elapsed_seconds as number).toFixed(2)}s`} />
      )}
    </>
  )
}

function Reflection({ r }: { r: Record<string, unknown> }) {
  const iters = (r.iterations as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <Section title="Final Code">
        <CodeBlock code={str(r.final_code)} />
      </Section>
      {iters.map((it, i) => (
        <Section key={i} title={`Iteration ${it.iteration ?? i + 1} — Critique`}>
          <p className="rr-prose rr-secondary">{str(it.critique)}</p>
        </Section>
      ))}
    </>
  )
}

function ToolUse({ r }: { r: Record<string, unknown> }) {
  const calls = (r.tool_calls_made as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <Section title="Final Answer">
        <p className="rr-prose">{str(r.final_answer)}</p>
      </Section>
      {calls.length > 0 && (
        <Section title={`Tools Used (${calls.length})`}>
          {calls.map((c, i) => (
            <div key={i} className="rr-tool-call">
              <span className="rr-tool-name">{str(c.name)}</span>
              <span className="rr-tool-result">→ {str(c.result)}</span>
            </div>
          ))}
        </Section>
      )}
    </>
  )
}

function Planning({ r }: { r: Record<string, unknown> }) {
  const steps = (r.plan as string[]) ?? []
  return (
    <>
      <Section title="Final Output">
        <p className="rr-prose">{str(r.final_output)}</p>
      </Section>
      <Section title="Plan Steps">
        <ol className="rr-list">
          {steps.map((s, i) => (
            <li key={i}>{str(s)}</li>
          ))}
        </ol>
      </Section>
    </>
  )
}

function MultiAgent({ r }: { r: Record<string, unknown> }) {
  return (
    <>
      <Section title="Final Article">
        <p className="rr-prose">{str(r.final_article)}</p>
      </Section>
      <Section title="Orchestration Plan">
        <p className="rr-prose rr-secondary">{str(r.orchestration_plan)}</p>
      </Section>
    </>
  )
}

function MemoryManagement({ r }: { r: Record<string, unknown> }) {
  const turns = (r.turns as Array<Record<string, unknown>>) ?? []
  const ltm = (r.ltm as Record<string, string>) ?? {}
  return (
    <>
      <Section title={`Long-term Memory (${Object.keys(ltm).length} facts)`}>
        {Object.entries(ltm).map(([k, v]) => (
          <div key={k} className="rr-kv">
            <span className="rr-kv-key">{k}</span>
            <span className="rr-kv-val">{str(v)}</span>
          </div>
        ))}
      </Section>
      <Section title="Conversation Turns">
        {turns.map((t, i) => (
          <div key={i} className="rr-turn">
            <div className="rr-turn-user">{str(t.user)}</div>
            <div className="rr-turn-assistant">{str(t.assistant)}</div>
          </div>
        ))}
      </Section>
    </>
  )
}

function LearningAdaptation({ r }: { r: Record<string, unknown> }) {
  const responses = (r.responses as Array<Record<string, unknown>>) ?? []
  const last = responses[responses.length - 1]
  const profile = (r.final_profile as Record<string, unknown>) ?? {}
  return (
    <>
      {last && (
        <Section title={`Final Response (Round ${str(last.round)})`}>
          <p className="rr-prose">{str(last.response)}</p>
        </Section>
      )}
      <Section title="Learned Profile">
        {Object.entries(profile).map(([k, v]) => (
          <div key={k} className="rr-kv">
            <span className="rr-kv-key">{k.replace(/_/g, ' ')}</span>
            <span className="rr-kv-val">{str(v)}</span>
          </div>
        ))}
      </Section>
    </>
  )
}

function ModelContextProtocol({ r }: { r: Record<string, unknown> }) {
  const tools = (r.tools_discovered as string[]) ?? []
  const resources = (r.resources_discovered as string[]) ?? []
  return (
    <>
      <Section title="Answer">
        <p className="rr-prose">{str(r.answer)}</p>
      </Section>
      <div className="rr-row">
        <Section title={`Tools (${tools.length})`}>
          <ul className="rr-list">{tools.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </Section>
        <Section title={`Resources (${resources.length})`}>
          <ul className="rr-list">{resources.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </Section>
      </div>
    </>
  )
}

function GoalMonitoring({ r }: { r: Record<string, unknown> }) {
  const milestones = (r.milestones as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <div className="rr-row">
        <Badge label="Overall Progress" value={`${r.overall_progress ?? 0}%`} />
        <Badge label="Status" value={str(r.status)} />
      </div>
      <Section title="Report">
        <p className="rr-prose">{str(r.report)}</p>
      </Section>
      <Section title="Milestones">
        {milestones.map((m, i) => (
          <div key={i} className="rr-milestone">
            <div className="rr-milestone-header">
              <span className="rr-milestone-id">{str(m.id ?? i + 1)}</span>
              <span className="rr-milestone-desc">{str(m.description)}</span>
              <span className={`rr-milestone-status rr-milestone-status--${str(m.status)}`}>
                {str(m.status)}
              </span>
            </div>
            <div className="rr-progress-bar">
              <div
                className="rr-progress-fill"
                style={{ width: `${m.progress_pct ?? 0}%` }}
              />
            </div>
          </div>
        ))}
      </Section>
    </>
  )
}

function ExceptionRecovery({ r }: { r: Record<string, unknown> }) {
  const scenarios = (r.scenarios as Array<Record<string, unknown>>) ?? []
  return (
    <>
      {scenarios.map((s, i) => (
        <Section key={i} title={str(s.label)}>
          <div className="rr-row">
            <Badge label="Recovered" value={s.recovered ? 'Yes' : 'No'} />
            <Badge label="Attempts" value={str(s.attempts)} />
          </div>
          {!!s.response && <p className="rr-prose rr-secondary">{str(s.response)}</p>}
        </Section>
      ))}
    </>
  )
}

function HumanInTheLoop({ r }: { r: Record<string, unknown> }) {
  const checkpoints = (r.checkpoints as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <Badge label="Status" value={str(r.status)} />
      {r.draft_preview && (
        <Section title="Draft Preview">
          <p className="rr-prose">{str(r.draft_preview)}</p>
        </Section>
      )}
      <Section title={`Checkpoints (${checkpoints.length})`}>
        {checkpoints.map((c, i) => (
          <div key={i} className="rr-kv">
            <span className="rr-kv-key">{str(c.id ?? c.checkpoint_type)}</span>
            <span className="rr-kv-val">{str(c.decision)}</span>
          </div>
        ))}
      </Section>
    </>
  )
}

function KnowledgeRetrieval({ r }: { r: Record<string, unknown> }) {
  const queries = (r.queries as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <div className="rr-row">
        <Badge label="Docs Indexed" value={str(r.documents_indexed)} />
        <Badge label="Chunks" value={str(r.chunks_indexed)} />
      </div>
      {queries.map((q, i) => (
        <Section key={i} title={str(q.question)}>
          <p className="rr-prose">{str(q.answer_preview ?? q.answer)}</p>
          <p className="rr-secondary rr-small">Sources: {str(q.sources_used)}</p>
        </Section>
      ))}
    </>
  )
}

function InterAgentCommunication({ r }: { r: Record<string, unknown> }) {
  return (
    <>
      <Section title="Final Article">
        <p className="rr-prose">{str(r.final_article)}</p>
      </Section>
      <Section title="Message Log">
        <pre className="rr-log">{str(r.message_log)}</pre>
      </Section>
    </>
  )
}

function ResourceOptimization({ r }: { r: Record<string, unknown> }) {
  const dist = (r.strategy_distribution as Record<string, number>) ?? {}
  return (
    <>
      <div className="rr-row">
        <Badge label="Completed" value={str(r.tasks_completed)} />
        <Badge label="Skipped" value={str(r.tasks_skipped)} />
        <Badge label="Tokens Used" value={str(r.tokens_used)} />
        <Badge label="Cost" value={`$${(r.cost_usd as number ?? 0).toFixed(5)}`} />
      </div>
      <Section title="Strategy Distribution">
        {Object.entries(dist).map(([k, v]) => (
          <div key={k} className="rr-kv">
            <span className="rr-kv-key">{k.replace(/_/g, ' ')}</span>
            <span className="rr-kv-val">{v} calls</span>
          </div>
        ))}
      </Section>
    </>
  )
}

function ReasoningTechniques({ r }: { r: Record<string, unknown> }) {
  const techniques = (r.techniques as Array<Record<string, unknown>>) ?? []
  return (
    <>
      {techniques.map((t, i) => (
        <Section key={i} title={`${str(t.name)} (${(t.elapsed_s as number ?? 0).toFixed(1)}s)`}>
          <p className="rr-prose rr-secondary">{str(t.output)}</p>
        </Section>
      ))}
    </>
  )
}

function GuardrailsSafety({ r }: { r: Record<string, unknown> }) {
  const cases = (r.test_cases as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <div className="rr-row">
        <Badge label="Passed" value={str(r.passed)} />
        <Badge label="Blocked" value={str(r.blocked)} />
      </div>
      {cases.map((c, i) => (
        <Section key={i} title={str(c.label)}>
          <div className="rr-row">
            <Badge label="Blocked" value={c.blocked ? 'Yes' : 'No'} />
            {!!c.block_reason && <Badge label="Reason" value={str(c.block_reason)} />}
          </div>
          <p className="rr-secondary rr-small">{str(c.summary)}</p>
        </Section>
      ))}
    </>
  )
}

function EvaluationMonitoring({ r }: { r: Record<string, unknown> }) {
  const scores = (r.aggregated_scores as Record<string, number>) ?? {}
  const alerts = (r.drift_alerts as Array<Record<string, unknown>>) ?? []
  return (
    <>
      <div className="rr-row">
        <Badge label="Suite Size" value={str(r.suite_size)} />
        <Badge label="A/B Winner" value={str(r.ab_winner)} />
      </div>
      <Section title="Aggregated Scores">
        {Object.entries(scores).map(([dim, score]) => (
          <div key={dim} className="rr-score">
            <span className="rr-score-label">{dim}</span>
            <div className="rr-score-bar">
              <div
                className="rr-score-fill"
                style={{ width: `${(score / 10) * 100}%` }}
              />
            </div>
            <span className="rr-score-val">{score.toFixed(1)}</span>
          </div>
        ))}
      </Section>
      {alerts.length > 0 && (
        <Section title={`Drift Alerts (${alerts.length})`}>
          {alerts.map((a, i) => (
            <div key={i} className="rr-kv rr-alert">
              <span className="rr-kv-key">{str(a.dimension)}</span>
              <span className="rr-kv-val">
                {(a.previous_avg as number).toFixed(1)} → {(a.current_avg as number).toFixed(1)} (Δ{(a.delta as number).toFixed(1)})
              </span>
            </div>
          ))}
        </Section>
      )}
    </>
  )
}

function Prioritization({ r }: { r: Record<string, unknown> }) {
  const order = (r.execution_order as string[]) ?? []
  return (
    <>
      <div className="rr-row">
        <Badge label="Executed" value={str(r.executed)} />
        <Badge label="Blocked" value={str(r.blocked)} />
        <Badge label="Top Task" value={str(r.top_task)} />
      </div>
      <Section title="Execution Order">
        <ol className="rr-list">
          {order.map((t, i) => <li key={i}>{t}</li>)}
        </ol>
      </Section>
    </>
  )
}

function ExplorationDiscovery({ r }: { r: Record<string, unknown> }) {
  const concepts = (r.concepts as string[]) ?? []
  return (
    <>
      <div className="rr-row">
        <Badge label="Seed" value={str(r.seed)} />
        <Badge label="Strategy" value={str(r.strategy)} />
        <Badge label="Nodes" value={str(r.nodes_discovered)} />
        <Badge label="Edges" value={str(r.edges_discovered)} />
      </div>
      <Section title="Insights">
        <p className="rr-prose">{str(r.insights)}</p>
      </Section>
      <Section title={`Discovered Concepts (${concepts.length})`}>
        <div className="rr-tags">
          {concepts.map((c, i) => (
            <span key={i} className="rr-tag">{c}</span>
          ))}
        </div>
      </Section>
    </>
  )
}

// ─── Generic fallback ─────────────────────────────────────────────────────

function GenericResult({ r }: { r: Record<string, unknown> }) {
  return (
    <Section title="Result">
      <pre className="rr-code rr-secondary">{JSON.stringify(r, null, 2)}</pre>
    </Section>
  )
}

// ─── Main dispatcher ─────────────────────────────────────────────────────

const RENDERERS: Record<number, (r: Record<string, unknown>) => React.ReactElement> = {
  1: (r) => <PromptChaining r={r} />,
  2: (r) => <Routing r={r} />,
  3: (r) => <Parallelization r={r} />,
  4: (r) => <Reflection r={r} />,
  5: (r) => <ToolUse r={r} />,
  6: (r) => <Planning r={r} />,
  7: (r) => <MultiAgent r={r} />,
  8: (r) => <MemoryManagement r={r} />,
  9: (r) => <LearningAdaptation r={r} />,
  10: (r) => <ModelContextProtocol r={r} />,
  11: (r) => <GoalMonitoring r={r} />,
  12: (r) => <ExceptionRecovery r={r} />,
  13: (r) => <HumanInTheLoop r={r} />,
  14: (r) => <KnowledgeRetrieval r={r} />,
  15: (r) => <InterAgentCommunication r={r} />,
  16: (r) => <ResourceOptimization r={r} />,
  17: (r) => <ReasoningTechniques r={r} />,
  18: (r) => <GuardrailsSafety r={r} />,
  19: (r) => <EvaluationMonitoring r={r} />,
  20: (r) => <Prioritization r={r} />,
  21: (r) => <ExplorationDiscovery r={r} />,
}

export default function ResultRenderer({ patternId, result }: Props) {
  const render = RENDERERS[patternId] ?? ((r) => <GenericResult r={r} />)
  return <div className="result-renderer">{render(result)}</div>
}
