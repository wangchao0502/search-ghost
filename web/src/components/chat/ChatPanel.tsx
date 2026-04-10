import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import type { SearchResult } from "../../api/client";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SearchResult[];
  streaming?: boolean;
}

interface ChatPanelProps {
  initialQuery?: string;
}

export default function ChatPanel({ initialQuery }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState(initialQuery ?? "");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");

    const userMsg: Message = { role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const allMessages = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const assistantMsg: Message = {
      role: "assistant",
      content: "",
      sources: [],
      streaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: allMessages, stream: true }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      if (!resp.body) throw new Error("No body");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));
          if (event.type === "sources") {
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = {
                ...copy[copy.length - 1],
                sources: event.results,
              };
              return copy;
            });
          } else if (event.type === "delta") {
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = {
                ...copy[copy.length - 1],
                content: copy[copy.length - 1].content + event.content,
              };
              return copy;
            });
          } else if (event.type === "done") {
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = {
                ...copy[copy.length - 1],
                streaming: false,
              };
              return copy;
            });
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          content: `Error: ${(err as Error).message}`,
          streaming: false,
        };
        return copy;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-16 text-sm">
            Ask a question about your knowledge base…
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-full bg-ghost-100 flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-4 h-4 text-ghost-600" />
              </div>
            )}
            <div className={`max-w-[80%] ${msg.role === "user" ? "order-first" : ""}`}>
              <div
                className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-ghost-500 text-white rounded-br-sm"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
                } ${msg.streaming ? "cursor-blink" : ""}`}
              >
                {msg.content || (msg.streaming ? "" : "…")}
              </div>
              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && !msg.streaming && (
                <div className="mt-2 space-y-1">
                  {msg.sources.slice(0, 3).map((s, si) => (
                    <div
                      key={s.chunk_id}
                      className="text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded-lg px-3 py-1.5"
                    >
                      <span className="font-medium text-ghost-600">[{si + 1}]</span>{" "}
                      {s.doc_title ?? s.doc_id.slice(0, 8)} —{" "}
                      {s.text.slice(0, 80)}…
                    </div>
                  ))}
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-4 h-4 text-gray-600" />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-xl border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ghost-300 focus:border-transparent"
            placeholder="Ask anything…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            disabled={loading}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="rounded-xl bg-ghost-500 text-white px-3 py-2 hover:bg-ghost-600 disabled:opacity-40 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
