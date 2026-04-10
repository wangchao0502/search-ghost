import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, FileText, RefreshCw } from "lucide-react";
import { listDocuments, deleteDocument, type DocumentMeta } from "../api/client";

const STATUS_COLOR: Record<DocumentMeta["status"], string> = {
  pending: "bg-yellow-100 text-yellow-700",
  processing: "bg-blue-100 text-blue-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function DocumentsPage() {
  const qc = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {isLoading && (
        <div className="text-center text-gray-400 py-16">Loading…</div>
      )}

      {data && data.length === 0 && (
        <div className="text-center text-gray-400 py-16 text-sm">
          No documents yet. Go to Ingest to add some.
        </div>
      )}

      <div className="space-y-2">
        {data?.map((doc) => (
          <div
            key={doc.doc_id}
            className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-3 hover:border-gray-300 transition-colors"
          >
            <FileText className="w-4 h-4 text-gray-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">{doc.title}</p>
              <p className="text-xs text-gray-400">
                {doc.chunk_count} chunks · {doc.char_count.toLocaleString()} chars ·{" "}
                {new Date(doc.created_at).toLocaleDateString()}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[doc.status]}`}
            >
              {doc.status}
            </span>
            <button
              onClick={() => {
                if (confirm(`Delete "${doc.title}"?`)) {
                  deleteMutation.mutate(doc.doc_id);
                }
              }}
              className="ml-1 p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
