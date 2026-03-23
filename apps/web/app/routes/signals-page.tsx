import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router";

// ─── helpers ────────────────────────────────────────────────────────────────

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift() ?? null;
  return null;
}

async function apiFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const csrfToken = getCookie("csrftoken");
  return fetch(url, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...(options.headers ?? {}),
    },
  });
}

// ─── types ───────────────────────────────────────────────────────────────────

interface Signal {
  id: string;
  title: string;
  content: string | null;
  processing_status: string;
  source: string;
  created_at: string;
}

// ─── status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    processed:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    insight_generated: "bg-accent-subtle text-accent-primary",
    error: "bg-danger-subtle text-danger-primary",
  };
  const cls = map[status] ?? "bg-surface-2 text-tertiary";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

export default function WorkspaceSignalsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  const [signals, setSignals] = useState<Signal[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isModalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = useCallback(async () => {
    if (!workspaceSlug || typeof window === "undefined") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/workspaces/${workspaceSlug}/signals/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSignals(Array.isArray(data) ? data : (data.results ?? []));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load signals");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceSlug || !title.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/workspaces/${workspaceSlug}/signals/`, {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          content,
          processing_status: "processed",
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      setModalOpen(false);
      setTitle("");
      setContent("");
      await fetchSignals();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create signal");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!workspaceSlug) return;
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/signals/${id}/`,
        { method: "DELETE" },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSignals((prev) => prev.filter((s) => s.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete signal");
    }
  };

  return (
    <div className="relative h-full w-full overflow-hidden overflow-y-auto">
      <div>
        <div className="mx-auto max-w-5xl px-6 py-8">
          {/* ── header ── */}
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-primary">
                Customer Signals
              </h1>
              <p className="mt-1 text-sm text-secondary">
                Capture raw feedback from users, support, and research.
              </p>
            </div>
            <button
              onClick={() => setModalOpen(true)}
              className="flex-shrink-0 rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 transition-colors"
            >
              + Add Signal
            </button>
          </div>

          {/* ── error banner ── */}
          {error && (
            <div className="mb-4 flex items-center justify-between rounded-md border border-red-200 bg-danger-subtle px-4 py-3 text-sm text-danger-primary dark:border-red-800">
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="ml-4 font-medium underline opacity-80 hover:opacity-100"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* ── table ── */}
          {isLoading && signals.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-sm text-tertiary">
              <svg
                className="mr-2 size-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z"
                />
              </svg>
              Loading signals…
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-subtle">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-subtle bg-surface-2">
                    <th className="px-4 py-3 font-medium text-secondary">
                      Title
                    </th>
                    <th className="px-4 py-3 font-medium text-secondary">
                      Content
                    </th>
                    <th className="px-4 py-3 font-medium text-secondary">
                      Status
                    </th>
                    <th className="px-4 py-3 font-medium text-secondary">
                      Date
                    </th>
                    <th className="px-4 py-3 font-medium text-secondary" />
                  </tr>
                </thead>
                <tbody>
                  {signals.map((sig) => (
                    <tr
                      key={sig.id}
                      className="border-b border-subtle bg-surface-1 last:border-0 hover:bg-surface-2 transition-colors"
                    >
                      <td className="px-4 py-3 font-medium text-primary">
                        {sig.title}
                      </td>
                      <td className="max-w-xs px-4 py-3 text-secondary">
                        <span className="line-clamp-2">
                          {sig.content ?? "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={sig.processing_status} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-tertiary">
                        {new Date(sig.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(sig.id)}
                          className="rounded p-1 text-tertiary hover:bg-danger-subtle hover:text-danger-primary transition-colors"
                          title="Delete signal"
                        >
                          <svg
                            className="size-4"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                          >
                            <path
                              d="M2 4h12M5 4V3h6v1M6 7v5M10 7v5M3 4l1 9h8l1-9"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}

                  {signals.length === 0 && !isLoading && (
                    <tr>
                      <td
                        colSpan={5}
                        className="bg-surface-1 px-4 py-16 text-center text-secondary"
                      >
                        <p className="mb-1 font-medium">No signals yet</p>
                        <p className="text-xs text-tertiary">
                          Click &ldquo;+ Add Signal&rdquo; to start capturing
                          feedback.
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── create modal ── */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl border border-subtle bg-surface-1 p-6 shadow-xl">
            <h2 className="mb-4 text-base font-semibold text-primary">
              New Signal
            </h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">
                  Title *
                </label>
                <input
                  className="w-full rounded-md border border-subtle bg-surface-2 px-3 py-2 text-sm text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                  placeholder="e.g. Users confused during onboarding"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">
                  Raw feedback
                </label>
                <textarea
                  className="w-full rounded-md border border-subtle bg-surface-2 px-3 py-2 text-sm text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                  placeholder="Paste raw feedback — messy is fine!"
                  rows={5}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>
              <div className="mt-1 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setModalOpen(false);
                    setTitle("");
                    setContent("");
                  }}
                  className="rounded-md border border-subtle px-3.5 py-2 text-sm font-medium text-secondary hover:bg-surface-2 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !title.trim()}
                  className="rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                  {isSubmitting ? "Submitting…" : "Submit"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
