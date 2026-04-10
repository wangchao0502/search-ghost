import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, MessageSquare } from "lucide-react";
import { searchKB, type SearchResult } from "../api/client";
import ChatPanel from "../components/chat/ChatPanel";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [chatQuery, setChatQuery] = useState<string | undefined>();

  const { data, isFetching } = useQuery({
    queryKey: ["search", submitted],
    queryFn: () => searchKB(submitted),
    enabled: !!submitted,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) setSubmitted(query.trim());
  };

  return (
    <div className="flex h-full">
      {/* Left: search */}
      <div className="flex-1 flex flex-col min-w-0 p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Search</h1>

        <form onSubmit={handleSubmit} className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-ghost-300 focus:border-transparent shadow-sm"
            placeholder="Search your knowledge base…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </form>

        {isFetching && (
          <div className="text-center text-gray-400 text-sm py-8">Searching…</div>
        )}

        {data && !isFetching && (
          <div className="space-y-3 overflow-y-auto">
            <p className="text-xs text-gray-400">
              {data.total} results for "{data.query}"
            </p>
            {data.results.map((r) => (
              <ResultCard key={r.chunk_id} result={r} onChat={() => setChatQuery(r.text)} />
            ))}
            {data.results.length === 0 && (
              <div className="text-center text-gray-400 text-sm py-8">
                No results found.
              </div>
            )}
          </div>
        )}

        {!submitted && !isFetching && (
          <div className="text-center text-gray-300 text-sm py-16">
            Type a query above and press Enter
          </div>
        )}
      </div>

      {/* Right: chat */}
      <div className="w-96 shrink-0 border-l border-gray-200 bg-gray-50 flex flex-col">
        <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-ghost-500" />
          <span className="text-sm font-semibold text-gray-700">RAG Chat</span>
        </div>
        <div className="flex-1 overflow-hidden">
          <ChatPanel initialQuery={chatQuery} />
        </div>
      </div>
    </div>
  );
}

function ResultCard({ result, onChat }: { result: SearchResult; onChat: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 hover:border-ghost-300 transition-colors shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-ghost-600 mb-1">
            {result.doc_title ?? result.doc_id.slice(0, 8)}
          </p>
          <p className="text-sm text-gray-700 leading-relaxed line-clamp-3">{result.text}</p>
        </div>
        <span className="text-xs text-gray-400 shrink-0 mt-0.5">
          {(result.score * 100).toFixed(1)}%
        </span>
      </div>
      <div className="mt-2 flex justify-end">
        <button
          onClick={onChat}
          className="text-xs text-ghost-500 hover:text-ghost-700 flex items-center gap-1"
        >
          <MessageSquare className="w-3 h-3" /> Ask about this
        </button>
      </div>
    </div>
  );
}
