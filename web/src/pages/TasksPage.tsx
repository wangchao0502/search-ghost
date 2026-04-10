import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { listTasks, type ProcessingTask } from "../api/client";

const STATUS_COLOR: Record<ProcessingTask["status"], string> = {
  pending: "bg-yellow-100 text-yellow-700",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function TasksPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => listTasks(50),
    refetchInterval: 3000,
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
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
          No tasks yet. Ingest a document to see tasks here.
        </div>
      )}

      <div className="space-y-2">
        {data?.map((task) => (
          <div
            key={task.task_id}
            className="bg-white border border-gray-200 rounded-xl px-4 py-3"
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-mono text-gray-600 truncate">
                  {task.task_id.slice(0, 16)}…
                </p>
                <p className="text-xs text-gray-400">
                  doc: {task.doc_id.slice(0, 12)}… · {new Date(task.created_at).toLocaleString()}
                </p>
                {task.error && (
                  <p className="text-xs text-red-500 mt-1">{task.error}</p>
                )}
              </div>
              <div className="text-right shrink-0">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[task.status]}`}
                >
                  {task.status}
                </span>
                {task.status === "processing" && (
                  <div className="mt-1.5 w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-ghost-500 transition-all"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
