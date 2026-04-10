import { Routes, Route, NavLink } from "react-router-dom";
import { Search, Upload, FileText, ListTodo } from "lucide-react";
import SearchPage from "./pages/SearchPage";
import IngestPage from "./pages/IngestPage";
import DocumentsPage from "./pages/DocumentsPage";
import TasksPage from "./pages/TasksPage";

const NAV = [
  { to: "/", icon: Search, label: "Search" },
  { to: "/ingest", icon: Upload, label: "Ingest" },
  { to: "/documents", icon: FileText, label: "Documents" },
  { to: "/tasks", icon: ListTodo, label: "Tasks" },
];

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-100">
          <span className="text-xl font-bold text-ghost-600 tracking-tight">
            👻 search-ghost
          </span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-ghost-50 text-ghost-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
        </Routes>
      </main>
    </div>
  );
}
