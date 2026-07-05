import { AlertTriangle, Bot, Clock, Coins, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ChatMessage, FollowUp } from "../../types";

interface Props {
  message: ChatMessage;
  onFollowUp: (query: string) => void;
}

export default function MessageBubble({ message, onFollowUp }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? "bg-indigo-600" : "bg-gray-200"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-gray-600" />
        )}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-indigo-600 text-white rounded-tr-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Guardrail badge */}
        {message.guardrail_triggered && (
          <div className="flex items-center gap-1 text-xs text-amber-600">
            <AlertTriangle className="w-3 h-3" />
            <span>Guardrail triggered</span>
          </div>
        )}

        {/* Meta: tokens + time */}
        {!isUser && (message.tokens_consumed || message.time_taken) && (
          <div className="flex items-center gap-3 text-xs text-gray-400">
            {message.tokens_consumed && (
              <span className="flex items-center gap-1">
                <Coins className="w-3 h-3" />
                {message.tokens_consumed.total} tokens
              </span>
            )}
            {message.time_taken !== undefined && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {message.time_taken.toFixed(2)}s
              </span>
            )}
          </div>
        )}

        {/* Follow-up suggestions */}
        {!isUser && message.follow_ups && message.follow_ups.length > 0 && (
          <div className="flex flex-col gap-1 mt-1 w-full">
            <p className="text-xs text-gray-400 font-medium">Related questions:</p>
            <div className="flex flex-wrap gap-1.5">
              {message.follow_ups.map((fu: FollowUp, i: number) => (
                <button
                  key={i}
                  onClick={() => onFollowUp(fu.query)}
                  className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full px-3 py-1 hover:bg-indigo-100 transition-colors text-left"
                >
                  {fu.text}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
