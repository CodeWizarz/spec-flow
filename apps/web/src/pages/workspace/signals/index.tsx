import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router";

const API_BASE = "/api"; // Proxied by Vite to :8000

async function apiGet(url: string) {
  const res = await fetch(`${API_BASE}${url}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPost(url: string, body: FormData | Record<string, unknown>) {
  const isFormData = body instanceof FormData;
  const res = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    credentials: "include",
    headers: isFormData ? {} : { "Content-Type": "application/json" },
    body: isFormData ? body : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function WorkspaceSignalsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const [signals, setSignals] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = useCallback(async () => {
    if (!workspaceSlug) return;
    setIsLoading(true);
    try {
      const data = await apiGet(`/workspaces/${workspaceSlug}/signals/`);
      setSignals(Array.isArray(data) ? data : data.results ?? []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceSlug) return;
    setIsLoading(true);
    try {
      await apiPost(`/workspaces/${workspaceSlug}/signals/`, { title, content, processing_status: "processed" });
      setModalOpen(false);
      setTitle("");
      setContent("");
      await fetchSignals();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Customer Signals</h1>
          <p className="text-gray-500 mt-1">Capture raw feedback from users, support, and research.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          + Add Signal
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
          Error: {error}{" "}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">New Signal</h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <input
                className="border rounded-lg p-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Signal Title (e.g. Users confused during onboarding)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
              <textarea
                className="border rounded-lg p-2 text-sm w-full min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Raw feedback content (messy is fine!)"
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
              <div className="flex justify-end gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {isLoading ? "Submitting..." : "Submit"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isLoading && signals.length === 0 ? (
        <p className="text-gray-500">Loading signals...</p>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="p-3 font-medium">Title</th>
                <th className="p-3 font-medium">Content</th>
                <th className="p-3 font-medium">Status</th>
                <th className="p-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((sig) => (
                <tr key={sig.id} className="border-b hover:bg-gray-50">
                  <td className="p-3 font-medium">{sig.title}</td>
                  <td className="p-3 text-gray-600 max-w-xs truncate">{sig.content}</td>
                  <td className="p-3">
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
                      {sig.processing_status}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500">{new Date(sig.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {signals.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-gray-400">
                    No signals yet. Click &quot;+ Add Signal&quot; to start capturing feedback.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
