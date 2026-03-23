import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router";

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

interface Memory {
  id: string;
  workspace: string;
  category: string;
  title: string;
  summary: string;
  metadata: Record<string, unknown>;
  spec: string | null;
  created_at: string;
  updated_at: string;
}

const CATEGORY_CONFIG: Record<
  string,
  { label: string; bg: string; text: string }
> = {
  shipped: {
    label: "Shipped",
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-700 dark:text-green-400",
  },
  rejected: {
    label: "Rejected",
    bg: "bg-red-100 dark:bg-red-900/30",
    text: "text-red-700 dark:text-red-400",
  },
  recurring_problem: {
    label: "Recurring Problem",
    bg: "bg-amber-100 dark:bg-amber-900/30",
    text: "text-amber-700 dark:text-amber-400",
  },
  spec_reference: {
    label: "Spec Ref",
    bg: "bg-accent-subtle",
    text: "text-accent-primary",
  },
};

function CategoryBadge({ category }: { category: string }) {
  const cfg = CATEGORY_CONFIG[category] ?? {
    label: category,
    bg: "bg-surface-2",
    text: "text-secondary",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}
    >
      {cfg.label}
    </span>
  );
}

const CATEGORIES = [
  { value: "", label: "All" },
  { value: "shipped", label: "Shipped" },
  { value: "rejected", label: "Rejected" },
  { value: "recurring_problem", label: "Recurring Problems" },
  { value: "spec_reference", label: "Spec References" },
];

export default function WorkspaceMemoryPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [filter, setFilter] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    category: "spec_reference",
    title: "",
    summary: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchMemories = useCallback(async () => {
    if (!workspaceSlug || typeof window === "undefined") return;
    setIsLoading(true);
    setError(null);
    try {
      const url = `/api/workspaces/${workspaceSlug}/memory/${filter ? `?category=${filter}` : ""}`;
      const res = await apiFetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMemories(Array.isArray(data) ? data : (data.results ?? []));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load memory");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, filter]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceSlug || !form.title.trim()) return;
    setIsSubmitting(true);
    try {
      const res = await apiFetch(`/api/workspaces/${workspaceSlug}/memory/`, {
        method: "POST",
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setModalOpen(false);
      setForm({ category: "spec_reference", title: "", summary: "" });
      await fetchMemories();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create memory");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!workspaceSlug) return;
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/memory/${id}/`,
        { method: "DELETE" },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  // Group by category for display
  const grouped = memories.reduce<Record<string, Memory[]>>((acc, m) => {
    (acc[m.category] = acc[m.category] ?? []).push(m);
    return acc;
  }, {});

  return (
    <div className="relative h-full w-full overflow-hidden overflow-y-auto">
      <div>
        <div className="mx-auto max-w-5xl px-6 py-8">
          {/* header */}
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-primary">
                Product Memory
              </h1>
              <p className="mt-1 text-sm text-secondary">
                Persistent context: shipped features, rejected ideas, and
                recurring problems. AI uses this to avoid duplicating work.
              </p>
            </div>
            <button
              onClick={() => setModalOpen(true)}
              className="flex-shrink-0 rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 transition-colors"
            >
              + Add Entry
            </button>
          </div>

          {/* filter tabs */}
          <div className="mb-5 flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                onClick={() => setFilter(c.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filter === c.value
                    ? "bg-accent-primary text-white"
                    : "border border-subtle bg-surface-2 text-secondary hover:bg-surface-1"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {/* error */}
          {error && (
            <div className="mb-4 flex items-center justify-between rounded-md border border-red-200 bg-danger-subtle px-4 py-3 text-sm text-danger-primary">
              <span>{error}</span>
              <button onClick={() => setError(null)} className="ml-4 underline">
                Dismiss
              </button>
            </div>
          )}

          {/* loading */}
          {isLoading && memories.length === 0 && (
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
              Loading product memory…
            </div>
          )}

          {/* content — grouped */}
          {!isLoading && memories.length > 0 && (
            <div className="space-y-8">
              {filter ? (
                <MemoryGroup
                  title={CATEGORY_CONFIG[filter]?.label ?? filter}
                  items={memories}
                  onDelete={handleDelete}
                />
              ) : (
                Object.entries(grouped).map(([cat, items]) => (
                  <MemoryGroup
                    key={cat}
                    title={CATEGORY_CONFIG[cat]?.label ?? cat}
                    items={items}
                    onDelete={handleDelete}
                  />
                ))
              )}
            </div>
          )}

          {/* empty */}
          {!isLoading && memories.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-subtle py-20 text-center">
              <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-surface-2 text-tertiary">
                <svg
                  className="size-6"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"
                  />
                </svg>
              </div>
              <p className="mb-1 text-base font-medium text-secondary">
                No memory entries yet
              </p>
              <p className="max-w-xs text-sm text-tertiary">
                Entries are created automatically when specs are completed,
                rejected, or generated. You can also add manual entries.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* create modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl border border-subtle bg-surface-1 p-6 shadow-xl">
            <h2 className="mb-4 text-base font-semibold text-primary">
              Add Memory Entry
            </h2>
            <form onSubmit={handleCreate} className="flex flex-col gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">
                  Category
                </label>
                <select
                  value={form.category}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, category: e.target.value }))
                  }
                  className="w-full rounded-md border border-subtle bg-surface-2 px-3 py-2 text-sm text-primary focus:border-accent-primary focus:outline-none"
                >
                  {CATEGORIES.filter((c) => c.value).map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">
                  Title *
                </label>
                <input
                  required
                  value={form.title}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, title: e.target.value }))
                  }
                  className="w-full rounded-md border border-subtle bg-surface-2 px-3 py-2 text-sm text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
                  placeholder="e.g. Dark mode redesign"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">
                  Summary
                </label>
                <textarea
                  rows={3}
                  value={form.summary}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, summary: e.target.value }))
                  }
                  className="w-full rounded-md border border-subtle bg-surface-2 px-3 py-2 text-sm text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
                  placeholder="Brief description of what was done, rejected, or learned"
                />
              </div>
              <div className="mt-1 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setModalOpen(false);
                    setForm({
                      category: "spec_reference",
                      title: "",
                      summary: "",
                    });
                  }}
                  className="rounded-md border border-subtle px-3.5 py-2 text-sm font-medium text-secondary hover:bg-surface-2 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !form.title.trim()}
                  className="rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
                >
                  {isSubmitting ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function MemoryGroup({
  title,
  items,
  onDelete,
}: {
  title: string;
  items: Memory[];
  onDelete: (id: string) => void;
}) {
  return (
    <div>
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-tertiary">
        {title} ({items.length})
      </h2>
      <div className="space-y-2">
        {items.map((m) => (
          <div
            key={m.id}
            className="group flex items-start gap-4 rounded-lg border border-subtle bg-surface-1 px-4 py-3 hover:bg-surface-2 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <CategoryBadge category={m.category} />
                <span className="font-medium text-sm text-primary truncate">
                  {m.title}
                </span>
              </div>
              {m.summary && (
                <p className="text-xs text-secondary line-clamp-2 mt-0.5">
                  {m.summary}
                </p>
              )}
            </div>
            <div className="flex flex-shrink-0 items-center gap-2">
              <span className="text-xs text-placeholder whitespace-nowrap">
                {new Date(m.created_at).toLocaleDateString()}
              </span>
              <button
                onClick={() => onDelete(m.id)}
                className="hidden rounded p-1 text-tertiary hover:bg-danger-subtle hover:text-danger-primary group-hover:block transition-colors"
                title="Delete"
              >
                <svg
                  className="size-3.5"
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
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
