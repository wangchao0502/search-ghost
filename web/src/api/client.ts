import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  timeout: 30_000,
});

// ── Types ─────────────────────────────────────────────────────────────────

export interface DocumentMeta {
  doc_id: string;
  title: string;
  source_url: string | null;
  content_type: string;
  tags: string[];
  status: "pending" | "processing" | "ready" | "failed";
  created_at: string;
  updated_at: string;
  chunk_count: number;
  char_count: number;
}

export interface SearchResult {
  chunk_id: string;
  doc_id: string;
  text: string;
  score: number;
  doc_title: string | null;
  source_url: string | null;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface ProcessingTask {
  task_id: string;
  doc_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  progress: number;
}

export interface IngestResponse {
  task_id: string;
  doc_id: string;
  message: string;
}

// ── API calls ─────────────────────────────────────────────────────────────

export async function searchKB(q: string, top_k = 6): Promise<SearchResponse> {
  const { data } = await api.get<SearchResponse>("/search", { params: { q, top_k } });
  return data;
}

export async function ingestFile(file: File, title?: string, tags?: string): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  if (tags) form.append("tags", tags);
  const { data } = await api.post<IngestResponse>("/ingest", form);
  return data;
}

export async function listDocuments(): Promise<DocumentMeta[]> {
  const { data } = await api.get<DocumentMeta[]>("/documents");
  return data;
}

export async function deleteDocument(doc_id: string): Promise<void> {
  await api.delete(`/documents/${doc_id}`);
}

export async function listTasks(limit = 50): Promise<ProcessingTask[]> {
  const { data } = await api.get<ProcessingTask[]>("/tasks", { params: { limit } });
  return data;
}

export async function getTask(task_id: string): Promise<ProcessingTask> {
  const { data } = await api.get<ProcessingTask>(`/tasks/${task_id}`);
  return data;
}
