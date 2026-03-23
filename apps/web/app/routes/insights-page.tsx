import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router";

// ─── helpers ─────────────────────────────────────────────────────────────────

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

// ─── types ────────────────────────────────────────────────────────────────────

interface Insight {
  id: string;
  theme: string;
  problem: string;
  root_cause: string;
  evidence: string[];
  frequency: number;
  created_at: string;
}

// ─── sub-components ───────────────────────────────────────────────────────────

function FrequencyPill({ count }: { count: number }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-accent-subtle px-2.5 py-0.5 text-xs font-semibold text-accent-primary">
      <svg className="size-3" viewBox="0 0 12 12" fill="currentColor">
        <path d="M6 1a5 5 0 100 10A5 5 0 006 1zm0 1.5a3.5 3.5 0 110 7 3.5 3.5 0 010-7zm0 1.5a.75.75 0 00-.75.75v2.25l1.5.9.375-.624-1.125-.675V4.75A.75.75 0 006 4z" />
      </svg>
      {count}× frequency
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-tertiary">
      {children}
    </p>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-subtle bg-surface-1 p-5 shadow-sm transition-shadow hover:shadow-md">
      {/* card header */}
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-semibold text-primary leading-snug">
          {insight.theme}
        </h2>
        <FrequencyPill count={insight.frequency} />
      </div>

      {/* problem */}
      <div>
        <SectionLabel>Core Problem</SectionLabel>
        <p className="text-sm text-primary">{insight.problem}</p>
      </div>

      {/* root cause */}
      {insight.root_cause && (
        <div>
          <SectionLabel>Root Cause</SectionLabel>
          <p className="text-sm text-primary">{insight.root_cause}</p>
        </div>
      )}

      {/* evidence quotes */}
      {Array.isArray(insight.evidence) && insight.evidence.length > 0 && (
        <div>
          <SectionLabel>Evidence</SectionLabel>
          <ul className="space-y-1.5 rounded-lg border border-subtle bg-surface-2 p-3">
            {insight.evidence.map((q, i) => (
              <li key={i} className="flex gap-1 text-sm italic text-secondary">
                <span className="flex-shrink-0 text-tertiary">&ldquo;</span>
                <span>{q}</span>
                <span className="flex-shrink-0 text-tertiary">&rdquo;</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* footer */}
      <p className="text-xs text-placeholder">
        {new Date(insight.created_at).toLocaleString()}
      </p>
    </div>
  );
}

// ─── main ─────────────────────────────────────────────────────────────────────

export default function WorkspaceInsightsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  const [insights, setInsights] = useState<Insight[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // ── fetch ──────────────────────────────────────────────────────────────────
  const fetchInsights = useCallback(async () => {
    if (!workspaceSlug || typeof window === "undefined") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/workspaces/${workspaceSlug}/insights/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setInsights(Array.isArray(data) ? data : (data.results ?? []));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load insights");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  // ── generate ───────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!workspaceSlug || isGenerating) return;
    setIsGenerating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/signals/generate/`,
        { method: "POST", body: JSON.stringify({}) },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      setSuccessMsg("⚡ Insight generation queued! Refreshing in 10 seconds…");
      // countdown + auto-refresh
      let secs = 10;
      setCountdown(secs);
      const tick = setInterval(() => {
        secs -= 1;
        setCountdown(secs);
        if (secs <= 0) {
          clearInterval(tick);
          setCountdown(null);
          setSuccessMsg(null);
          fetchInsights();
        }
      }, 1000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to queue generation");
    } finally {
      setIsGenerating(false);
    }
  };

  // ── delete ─────────────────────────────────────────────────────────────────
  const handleDelete = async (id: string) => {
    if (!workspaceSlug) return;
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/insights/${id}/`,
        { method: "DELETE" },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setInsights((prev) => prev.filter((ins) => ins.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete insight");
    }
  };

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="relative h-full w-full overflow-hidden overflow-y-auto">
      <div>
        <div className="mx-auto max-w-5xl px-6 py-8">
          {/* ── page header ── */}
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-primary">
                AI Insights
              </h1>
              <p className="mt-1 text-sm text-secondary">
                Recurring themes and root causes extracted from raw signals.
              </p>
            </div>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex-shrink-0 rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {isGenerating ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="size-3.5 animate-spin"
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
                  Generating…
                </span>
              ) : (
                "⚡ Generate Insights"
              )}
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

          {/* ── success banner ── */}
          {successMsg && (
            <div className="mb-4 flex items-center justify-between rounded-md border border-green-200 bg-success-subtle px-4 py-3 text-sm text-success-primary dark:border-green-800">
              <span>
                {successMsg}
                {countdown !== null && (
                  <span className="ml-2 font-semibold">{countdown}s</span>
                )}
              </span>
              <button
                onClick={() => {
                  setSuccessMsg(null);
                  setCountdown(null);
                }}
                className="ml-4 font-medium underline opacity-80 hover:opacity-100"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* ── loading ── */}
          {isLoading && insights.length === 0 && (
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
              Loading insights…
            </div>
          )}

          {/* ── insight cards ── */}
          {!isLoading && insights.length > 0 && (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              {insights.map((insight) => (
                <div key={insight.id} className="relative group">
                  <InsightCard insight={insight} />
                  {/* delete button appears on hover */}
                  <button
                    onClick={() => handleDelete(insight.id)}
                    className="absolute right-3 top-3 hidden rounded p-1 text-tertiary hover:bg-danger-subtle hover:text-danger-primary group-hover:flex transition-colors"
                    title="Delete insight"
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
              ))}
            </div>
          )}

          {/* ── empty state ── */}
          {!isLoading && insights.length === 0 && (
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
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <p className="mb-1 text-base font-medium text-secondary">
                No insights yet
              </p>
              <p className="max-w-xs text-sm text-tertiary">
                Add signals first, then click &ldquo;Generate Insights&rdquo; to
                extract themes with AI.
              </p>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="mt-5 rounded-md bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
              >
                ⚡ Generate Insights
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
