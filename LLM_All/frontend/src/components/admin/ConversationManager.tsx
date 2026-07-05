import {
  BarChart3,
  Bot,
  ChevronRight,
  Clock,
  Coins,
  Lightbulb,
  MessageSquare,
  User,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { adminApi } from "../../api/client";
import {
  AnalyticsOut,
  ConversationDetail,
  ConversationOut,
  InsightsOut,
  SummaryOut,
} from "../../types";

// ── Conversation list ──────────────────────────────────────────────────────

function ConversationList({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const [convs, setConvs] = useState<ConversationOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi
      .listConversations()
      .then(({ data }) => setConvs(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-400 text-sm p-4">Loading…</div>;

  return (
    <div className="space-y-2">
      {convs.length === 0 && (
        <p className="text-gray-400 text-sm">No conversations yet.</p>
      )}
      {convs.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          className="w-full text-left bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <User className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                <span className="font-medium text-gray-900 text-sm">{c.username}</span>
                {c.llm_provider && (
                  <span className="badge bg-indigo-50 text-indigo-700">{c.llm_provider}</span>
                )}
              </div>
              <p className="text-sm text-gray-600 truncate">{c.title}</p>
              <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" />
                  {c.message_count} messages
                </span>
                <span>{new Date(c.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-indigo-500 transition-colors" />
          </div>
        </button>
      ))}
    </div>
  );
}

// ── Conversation detail panel ─────────────────────────────────────────────

type Tab = "messages" | "analytics" | "summary" | "insights";

function ConversationDetailPanel({
  conversationId,
  onClose,
}: {
  conversationId: string;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("messages");
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsOut | null>(null);
  const [summary, setSummary] = useState<SummaryOut | null>(null);
  const [insights, setInsights] = useState<InsightsOut | null>(null);
  const [loadingTab, setLoadingTab] = useState(false);
  const [tabError, setTabError] = useState("");

  useEffect(() => {
    adminApi.getConversation(conversationId).then(({ data }) => setDetail(data));
  }, [conversationId]);

  const loadTab = async (t: Tab) => {
    setTab(t);
    setTabError("");
    if (t === "messages") return;
    setLoadingTab(true);
    try {
      if (t === "analytics" && !analytics) {
        const { data } = await adminApi.getAnalytics(conversationId);
        setAnalytics(data);
      } else if (t === "summary" && !summary) {
        const { data } = await adminApi.getSummary(conversationId);
        setSummary(data);
      } else if (t === "insights" && !insights) {
        const { data } = await adminApi.getInsights(conversationId);
        setInsights(data);
      }
    } catch (err: any) {
      setTabError(err.response?.data?.detail || "Failed to load data");
    } finally {
      setLoadingTab(false);
    }
  };

  const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "messages", label: "Messages", icon: <MessageSquare className="w-4 h-4" /> },
    { key: "analytics", label: "Analytics", icon: <BarChart3 className="w-4 h-4" /> },
    { key: "summary", label: "Summary", icon: <Bot className="w-4 h-4" /> },
    { key: "insights", label: "Insights", icon: <Lightbulb className="w-4 h-4" /> },
  ];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h3 className="font-semibold text-gray-900">{detail?.title || "Conversation"}</h3>
            <p className="text-xs text-gray-500">
              {detail?.username} · {conversationId.slice(0, 8)}…
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-6 pt-3 border-b border-gray-200">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => loadTab(t.key)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                tab === t.key
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loadingTab && (
            <div className="flex items-center justify-center h-32 text-gray-400">
              Generating with AI…
            </div>
          )}
          {tabError && !loadingTab && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {tabError}
            </div>
          )}

          {/* Messages */}
          {tab === "messages" && detail && !loadingTab && (
            <div className="space-y-3">
              {detail.messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center ${
                      m.role === "user" ? "bg-indigo-600" : "bg-gray-200"
                    }`}
                  >
                    {m.role === "user" ? (
                      <User className="w-3.5 h-3.5 text-white" />
                    ) : (
                      <Bot className="w-3.5 h-3.5 text-gray-600" />
                    )}
                  </div>
                  <div className="max-w-[80%] space-y-1">
                    <div
                      className={`rounded-xl px-3 py-2 text-sm ${
                        m.role === "user"
                          ? "bg-indigo-600 text-white"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    </div>
                    {m.role === "assistant" && (
                      <div className="flex gap-3 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                          <Coins className="w-3 h-3" />
                          {m.tokens_in + m.tokens_out} tokens
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {m.time_taken.toFixed(2)}s
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Analytics */}
          {tab === "analytics" && analytics && !loadingTab && (
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Total Messages", value: analytics.total_messages },
                { label: "User Messages", value: analytics.user_messages },
                { label: "AI Responses", value: analytics.assistant_messages },
                { label: "Total Tokens", value: analytics.total_tokens.toLocaleString() },
                {
                  label: "Avg Tokens / Response",
                  value: analytics.avg_tokens_per_response.toFixed(1),
                },
                { label: "Avg Response Time", value: `${analytics.avg_response_time.toFixed(3)}s` },
                {
                  label: "Session Duration",
                  value: `${analytics.session_duration_minutes.toFixed(1)} min`,
                },
                { label: "Guardrail Triggers", value: analytics.guardrail_triggers },
                { label: "LLM Provider", value: analytics.llm_provider || "—" },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-50 rounded-xl p-4">
                  <p className="text-xs text-gray-500 font-medium">{label}</p>
                  <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Summary */}
          {tab === "summary" && summary && !loadingTab && (
            <div className="space-y-3">
              <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
                <p className="text-sm font-medium text-indigo-700 mb-2">AI-Generated Summary</p>
                <p className="text-gray-800 leading-relaxed text-sm">{summary.summary}</p>
              </div>
              <p className="text-xs text-gray-400">
                Generated at {new Date(summary.generated_at).toLocaleString()}
              </p>
            </div>
          )}

          {/* Insights */}
          {tab === "insights" && insights && !loadingTab && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">Sentiment:</span>
                <span
                  className={`badge ${
                    insights.sentiment === "positive"
                      ? "bg-green-100 text-green-700"
                      : insights.sentiment === "negative"
                      ? "bg-red-100 text-red-700"
                      : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {insights.sentiment}
                </span>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Topics</p>
                <div className="flex flex-wrap gap-1.5">
                  {insights.topics.map((t, i) => (
                    <span key={i} className="badge bg-purple-50 text-purple-700">
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Key Insights</p>
                <ul className="space-y-2">
                  {insights.insights.map((ins, i) => (
                    <li key={i} className="flex gap-2 text-sm text-gray-700">
                      <span className="text-indigo-500 font-bold mt-0.5">•</span>
                      {ins}
                    </li>
                  ))}
                </ul>
              </div>

              <p className="text-xs text-gray-400">
                Generated at {new Date(insights.generated_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function ConversationManager() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Conversation Management</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          View all conversations and access analytics, summaries, and insights.
        </p>
      </div>

      <ConversationList onSelect={setSelectedId} />

      {selectedId && (
        <ConversationDetailPanel
          conversationId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
