import { useState, useRef } from "react";
import { Upload, CheckCircle, XCircle, Loader2, FileText } from "lucide-react";
import { ingestFile, type IngestResponse } from "../api/client";
import { useQueryClient } from "@tanstack/react-query";

interface UploadItem {
  file: File;
  status: "idle" | "uploading" | "done" | "error";
  response?: IngestResponse;
  error?: string;
}

export default function IngestPage() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const addFiles = (files: FileList | File[]) => {
    const newItems: UploadItem[] = Array.from(files).map((f) => ({
      file: f,
      status: "idle",
    }));
    setItems((prev) => [...prev, ...newItems]);
    newItems.forEach((_, i) => uploadItem(items.length + i, newItems[i]));
  };

  const uploadItem = async (index: number, item: UploadItem) => {
    setItems((prev) =>
      prev.map((it, i) => (it === item ? { ...it, status: "uploading" } : it))
    );
    try {
      const resp = await ingestFile(item.file);
      setItems((prev) =>
        prev.map((it) => (it === item ? { ...it, status: "done", response: resp } : it))
      );
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    } catch (err) {
      setItems((prev) =>
        prev.map((it) =>
          it === item ? { ...it, status: "error", error: String(err) } : it
        )
      );
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Ingest Documents</h1>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors mb-6 ${
          dragging
            ? "border-ghost-400 bg-ghost-50"
            : "border-gray-300 hover:border-ghost-300 hover:bg-gray-50"
        }`}
      >
        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-600 font-medium">
          Drop files here or <span className="text-ghost-600 underline">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Markdown, plain text (Phase 1) — more formats coming in Phase 2
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".md,.txt,.markdown"
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {/* File list */}
      {items.length > 0 && (
        <div className="space-y-2">
          {items.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-3"
            >
              <FileText className="w-4 h-4 text-gray-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{item.file.name}</p>
                {item.response && (
                  <p className="text-xs text-gray-400">
                    task: {item.response.task_id.slice(0, 8)}…
                  </p>
                )}
                {item.error && (
                  <p className="text-xs text-red-500">{item.error}</p>
                )}
              </div>
              <StatusIcon status={item.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: UploadItem["status"] }) {
  if (status === "uploading")
    return <Loader2 className="w-4 h-4 text-ghost-500 animate-spin" />;
  if (status === "done")
    return <CheckCircle className="w-4 h-4 text-green-500" />;
  if (status === "error")
    return <XCircle className="w-4 h-4 text-red-500" />;
  return <div className="w-4 h-4 rounded-full border-2 border-gray-300" />;
}
