import { Bot, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { chatApi } from "../../api/client";
import { ChatMessage } from "../../types";
import MessageBubble from "./MessageBubble";

interface Props {
  conversationId: string;
}

export default function ChatWindow({ conversationId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Load existing history on mount
    chatApi.getHistory(conversationId).then(({ data }) => {
      const hist: ChatMessage[] = data.messages.map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        guardrail_triggered: m.guardrail_triggered,
        timestamp: m.created_at,
      }));
      setMessages(hist);
    });
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setInput("");
    setError("");

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const { data } = await chatApi.sendMessage(conversationId, trimmed);
      const botMsg: ChatMessage = {
        id: data.message_id,
        role: "assistant",
        content: data.response,
        follow_ups: data.follow_ups,
        tokens_consumed: data.tokens_consumed,
        time_taken: data.time_taken,
        guardrail_triggered: data.guardrail_triggered,
        timestamp: data.timestamp,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to get response. Please try again.");
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 py-16">
            <Bot className="w-12 h-12 mb-3 text-gray-300" />
            <p className="text-lg font-medium text-gray-500">Start a conversation</p>
            <p className="text-sm">Ask anything — I'm here to help.</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onFollowUp={send} />
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-gray-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-4">
        <div className="flex gap-2 items-end max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
            rows={1}
            className="flex-1 input-field resize-none max-h-40 overflow-y-auto"
            style={{ minHeight: "42px" }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = `${Math.min(t.scrollHeight, 160)}px`;
            }}
            disabled={loading}
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || loading}
            className="btn-primary flex-shrink-0 flex items-center gap-1.5 h-[42px]"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          AI responses may contain errors. Verify important information.
        </p>
      </div>
    </div>
  );
}
