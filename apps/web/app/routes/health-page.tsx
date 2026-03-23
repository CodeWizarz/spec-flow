import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router";

// ─── helpers ──────────────────────────────────────────────────────────────────

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift() ?? null;
  return null;
}

async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
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

interface SourceBreakdown {
  source: string;
  count: number;
}

interface InsightTheme {
  theme: string;
  problem: string;
  frequency: number;
}

interface PrioritySpec {
  id: string;
  title: string;
  priority_score: number;
  impact_score: number;
  effort_score: number;
  status: string;
}

interface Alert {
  type: string;
  message: string;
  severity: "high" | "medium" | "low" | "info";
}

interface HealthData {
  signals: {
    total: number;
    last_1h: number;
    last_24h: number;
    last_7d: number;
    spike_detected: boolean;
    by_source: SourceBreakdown[];
  };
  insights: {
    total: number;
    top_themes: InsightTheme[];
    recurring_problems: InsightTheme[];
  };
  specs: {
    total: number;
    by_status: Array<{ status: string; count: number }>;
    priority_queue: PrioritySpec[];
  };
  memory_context: string;
  alerts: Alert[];
}

// ─── sub-components ───────────────────────────────────────────────────────────

function Spinner({ className = "size-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
    </svg>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-tertiary">
      {children}
    </p>
  );
}

function AlertBanner({ alert }: { alert: Alert }) {
  const cfg: Record<string, string> = {
    high: "bg-danger-subtle border-red-200 text-danger-primary dark:border-red-800",
    medium: "bg-warning-subtle border-amber-200 text-warning-primary dark:border-amber-800",
    low: "bg-surface-2 border-subtle text-secondary",
    info: "bg-accent-subtle border-accent-primary/20 text-accent-primary",
  };
  const icons: Record<string, string> = {
    high: "🚨",
    medium: "⚠️",
    low: "ℹ️",
    info: "💡",
  };
  const cls = cfg[alert.severity] ?? cfg.info;
  return (
    <div className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${cls}`}>
      <span className="flex-shrink-0 text-base">{icons[alert.severity] ?? "ℹ️"}</span>
      <p className="leading-snug">{alert.message}</p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string | number;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`flex flex-col gap-1 rounded-xl border p-4 ${
        highlight
          ? "border-red-300 bg-danger-subtle/60 dark:border-red-700"
          : "border-subtle bg-surface-1"
      }`}
    >
      <p className="text-xs font-medium text-tertiary">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? "text-danger-primary" : "text-primary"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-placeholder">{sub}</p>}
    </div>
  );
}

function PriorityBar({ score, max = 10 }: { score: number; max?: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const color =
    score >= 7 ? "bg-green-500" : score >= 4 ? "bg-accent-primary" : "bg-amber-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-xs font-semibold text-secondary">
        {score.toFixed(1)}
      </span>
    </div>
  );
}

function PriorityQueueCard({
  spec,
  rank,
  workspaceSlug,
}: {
  spec: PrioritySpec;
  rank: number;
  workspaceSlug: string;
}) {
  return (
    <a
      href={`/${workspaceSlug}/specs`}
      className="group flex items-start gap-4 rounded-xl border border-subtle bg-surface-1 px-4 py-3 transition-all hover:border-accent-primary/40 hover:bg-surface-2"
    >
      {/* rank badge */}
      <div
        className={`mt-0.5 flex size-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          rank === 1
            ? "bg-accent-primary text-white"
            : "bg-surface-2 text-secondary"
        }`}
      >
        {rank}
      </div>

      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-primary group-hover:text-accent-primary">
          {spec.title}
        </p>
        <div className="mt-1.5 grid grid-cols-3 gap-2 text-xs">
          <div>
            <span className="text-placeholder">Impact </span>
            <span className="font-semibold text-secondary">{spec.impact_score.toFixed(1)}</span>
          </div>
          <div>
            <span className="text-placeholder">Effort </span>
            <span className="font-semibold text-secondary">{spec.effort_score.toFixed(1)}</span>
          </div>
          <div>
            <span className="text-placeholder">Priority </span>
            <span className="font-semibold text-accent-primary">{spec.priority_score.toFixed(2)}</span>
          </div>
        </div>
        <div className="mt-2">
          <PriorityBar score={spec.priority_score} />
        </div>
      </div>
    </a>
  );
}

function SourceBreakdownRow({ item, max }: { item: SourceBreakdown; max: number }) {
  const pct = max > 0 ? Math.round((item.count / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-20 flex-shrink-0 truncate text-xs font-medium capitalize text-secondary">
        {item.source}
      </span>
      <div className="flex flex-1 items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
          <div
            className="h-full rounded-full bg-accent-primary/70 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="w-6 text-right text-xs text-tertiary">{item.count}</span>
      </div>
    </div>
  );
}

function InsightRow({ insight, workspaceSlug }: { insight: InsightTheme; workspaceSlug: string }) {
  return (
    <a
      href={`/${workspaceSlug}/insights`}
      className="group flex items-start gap-3 rounded-lg border border-subtle bg-surface-1 px-4 py-3 hover:bg-surface-2 transition-colors"
    >
      <span className="mt-0.5 flex-shrink-0 rounded-full bg-accent-subtle px-1.5 py-0.5 text-xs font-semibold text-accent-primary">
        {insight.frequency}×
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-semibold text-primary group-hover:text-accent-primary">
          {insight.theme}
        </p>
        <p className="mt-0.5 line-clamp-1 text-xs text-secondary">{insight.problem}</p>
      </div>
    </a>
  );
}

function MemoryContextPanel({ context }: { context: string }) {
  const [expanded, setExpanded] = useState(false);
  if (!context) {
    return (
      <div className="rounded-xl border border-dashed border-subtle bg-surface-2 px-4 py-6 text-center">
        <p className="text-xs text-placeholder">
          No Supermemory context yet.{" "}
          <a
            href="https://console.supermemory.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent-primary underline"
          >
            Add your SUPERMEMORY_API_KEY
          </a>{" "}
          to enable semantic product memory.
        </p>
      </div>
    );
  }

  const lines = context.split("\n").filter(Boolean);
  const preview = lines.slice(0, 3);
  const rest = lines.slice(3);

  return (
    <div className="rounded-xl border border-subtle bg-surface-1">
      <div className="px-4 py-3">
        <ul className="space-y-1.5">
          {preview.map((line, i) => (
            <li key={i} className="text-xs text-secondary leading-relaxed">
              {line}
            </li>
          ))}
          {expanded &&
            rest.map((line, i) => (
              <li key={`r${i}`} className="text-xs text-secondary leading-relaxed">
                {line}
              </li>
            ))}
        </ul>
        {rest.length > 0 && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 text-xs text-accent-primary underline"
          >
            {expanded ? "Show less" : `Show ${rest.length} more lines`}
          </button>
        )}
      </div>
    </div>
  );
}

// ─── lifecycle breadcrumb ─────────────────────────────────────────────────────

function LifecycleBreadcrumb({ workspaceSlug }: { workspaceSlug: string }) {
  const steps = [
    { label: "Signals", href: `/${workspaceSlug}/signals`, icon: "📡" },
    { label: "Insights", href: `/${workspaceSlug}/insights`, icon: "🧠" },
    { label: "Specs", href: `/${workspaceSlug}/specs`, icon: "📋" },
    { label: "Memory", href: `/${workspaceSlug}/memory`, icon: "🗂️" },
    { label: "Health", href: `/${workspaceSlug}/health`, icon: "📊" },
  ];
  return (
    <div className="mb-6 flex flex-wrap items-center gap-1 rounded-lg border border-subtle bg-surface-2 px-4 py-2 text-xs">
      {steps.map((step, i) => (
        <React.Fragment key={step.label}>
          <a
            href={step.href}
            className={`flex items-center gap-1.5 rounded-md px-2 py-1 font-medium transition-colors hover:bg-surface-1 ${
              step.label === "Health"
                ? "bg-accent-primary text-white"
                : "text-secondary hover:text-primary"
            }`}
          >
            <span>{step.icon}</span>
            {step.label}
          </a>
          {i < steps.length - 1 && (
            <svg className="size-3 text-placeholder" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M6 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function WorkspaceHealthPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  const [data, setData] = useState<HealthData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Semantic memory search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<unknown[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const fetchHealth = useCallback(
    async (silent = false) => {
      if (!workspaceSlug || typeof window === "undefined") return;
      if (silent) setIsRefreshing(true);
      else setIsLoading(true);
      setError(null);
      try {
        const res = await apiFetch(`/api/workspaces/${workspaceSlug}/health/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: HealthData = await res.json();
        setData(json);
        setLastRefresh(new Date());
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load health data");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [workspaceSlug],
  );

  // Initial load + auto-refresh every 60 s
  useEffect(() => {
    fetchHealth();
    const timer = setInterval(() => fetchHealth(true), 60_000);
    return () => clearInterval(timer);
  }, [fetchHealth]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceSlug || !searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await apiFetch(`/api/workspaces/${workspaceSlug}/memory/search/`, {
        method: "POST",
        body: JSON.stringify({ query: searchQuery, limit: 8 }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setSearchResults(json.results ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setIsSearching(false);
    }
  };

  if (isLoading) {
    return (
      <div className="relative h-full w-full overflow-hidden overflow-y-auto">
        <div className="flex h-full items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-secondary">
            <Spinner className="size-8" />
            <p className="text-sm">Loading product health…</p>
          </div>
        </div>
      </div>
    );
  }

  const totalSignals = data?.signals.total ?? 0;
  const maxSource = Math.max(...(data?.signals.by_source.map((s) => s.count) ?? [1]));

  return (
    <div className="relative h-full w-full overflow-hidden overflow-y-auto">
      <div>
        <div className="mx-auto max-w-5xl px-6 py-8">

          {/* lifecycle nav */}
          {workspaceSlug && <LifecycleBreadcrumb workspaceSlug={workspaceSlug} />}

          {/* page header */}
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-primary">Product Health</h1>
              <p className="mt-1 text-sm text-secondary">
                Real-time signal velocity, insight trends, and autonomous prioritization.
                {lastRefresh && (
                  <span className="ml-2 text-placeholder">
                    Last updated {lastRefresh.toLocaleTimeString()}
                  </span>
                )}
              </p>
            </div>
            <button
              onClick={() => fetchHealth(true)}
              disabled={isRefreshing}
              className="flex flex-shrink-0 items-center gap-1.5 rounded-md border border-subtle bg-surface-1 px-3.5 py-2 text-sm font-medium text-secondary hover:bg-surface-2 disabled:opacity-50 transition-colors"
            >
              {isRefreshing ? <Spinner className="size-3.5" /> : (
                <svg className="size-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M13.5 2.5A6.5 6.5 0 1114 8" strokeLinecap="round" />
                  <path d="M14 2.5V6h-3.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              Refresh
            </button>
          </div>

          {/* error */}
          {error && (
            <div className="mb-5 flex items-center justify-between rounded-md border border-red-200 bg-danger-subtle px-4 py-3 text-sm text-danger-primary dark:border-red-800">
              <span>{error}</span>
              <button onClick={() => setError(null)} className="ml-4 underline">Dismiss</button>
            </div>
          )}

          {data && (
            <>
              {/* ── alerts ── */}
              {data.alerts.length > 0 && (
                <div className="mb-6 space-y-2">
                  {data.alerts.map((alert, i) => (
                    <AlertBanner key={i} alert={alert} />
                  ))}
                </div>
              )}

              {/* ── signal velocity tiles ── */}
              <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetricTile
                  label="Signals (1h)"
                  value={data.signals.last_1h}
                  highlight={data.signals.spike_detected}
                  sub={data.signals.spike_detected ? "⚡ Spike!" : undefined}
                />
                <MetricTile label="Signals (24h)" value={data.signals.last_24h} />
                <MetricTile label="Signals (7d)" value={data.signals.last_7d} />
                <MetricTile label="Signals total" value={totalSignals} />
              </div>

              {/* ── main grid ── */}
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">

                {/* Signal sources */}
                <div className="rounded-xl border border-subtle bg-surface-1 p-5">
                  <SectionLabel>Signal Sources</SectionLabel>
                  {data.signals.by_source.length === 0 ? (
                    <p className="text-xs italic text-placeholder">No signals yet.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {data.signals.by_source.map((item) => (
                        <SourceBreakdownRow key={item.source} item={item} max={maxSource} />
                      ))}
                    </div>
                  )}
                </div>

                {/* Spec status distribution */}
                <div className="rounded-xl border border-subtle bg-surface-1 p-5">
                  <SectionLabel>Spec Pipeline</SectionLabel>
                  <div className="grid grid-cols-2 gap-3">
                    {(["proposed", "in_progress", "completed", "rejected"] as const).map((s) => {
                      const count =
                        data.specs.by_status.find((x) => x.status === s)?.count ?? 0;
                      const cfgMap: Record<string, string> = {
                        proposed: "bg-surface-2 text-secondary",
                        in_progress: "bg-accent-subtle text-accent-primary",
                        completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
                        rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
                      };
                      const labels: Record<string, string> = {
                        proposed: "Proposed",
                        in_progress: "In Progress",
                        completed: "Completed",
                        rejected: "Rejected",
                      };
                      return (
                        <div
                          key={s}
                          className={`flex flex-col gap-0.5 rounded-lg px-3 py-2.5 ${cfgMap[s]}`}
                        >
                          <span className="text-xl font-bold">{count}</span>
                          <span className="text-xs font-medium opacity-80">{labels[s]}</span>
                        </div>
                      );
                    })}
                  </div>
                  <p className="mt-3 text-xs text-tertiary">{data.specs.total} total specs</p>
                </div>
              </div>

              {/* ── priority queue ── */}
              {data.specs.priority_queue.length > 0 && (
                <div className="mt-6 rounded-xl border border-subtle bg-surface-1 p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <SectionLabel>🎯 Build-Next Priority Queue</SectionLabel>
                    <span className="text-xs text-placeholder">Scored by impact ÷ effort</span>
                  </div>
                  <div className="space-y-2">
                    {data.specs.priority_queue.map((spec, i) => (
                      <PriorityQueueCard
                        key={spec.id}
                        spec={spec}
                        rank={i + 1}
                        workspaceSlug={workspaceSlug ?? ""}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* ── insights grid ── */}
              <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">

                {/* Top themes */}
                <div className="rounded-xl border border-subtle bg-surface-1 p-5">
                  <SectionLabel>Top Insight Themes</SectionLabel>
                  {data.insights.top_themes.length === 0 ? (
                    <p className="text-xs italic text-placeholder">No insights yet. Generate some from Signals.</p>
                  ) : (
                    <div className="space-y-2">
                      {data.insights.top_themes.map((insight, i) => (
                        <InsightRow key={i} insight={insight} workspaceSlug={workspaceSlug ?? ""} />
                      ))}
                    </div>
                  )}
                </div>

                {/* Recurring problems */}
                <div className="rounded-xl border border-subtle bg-surface-1 p-5">
                  <SectionLabel>🔁 Recurring Problems (freq ≥ 3)</SectionLabel>
                  {data.insights.recurring_problems.length === 0 ? (
                    <p className="text-xs italic text-placeholder">
                      No recurring problems detected yet. They appear when the same theme recurs 3+ times.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {data.insights.recurring_problems.map((insight, i) => (
                        <InsightRow key={i} insight={insight} workspaceSlug={workspaceSlug ?? ""} />
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* ── supermemory context ── */}
              <div className="mt-6 rounded-xl border border-subtle bg-surface-1 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <SectionLabel>🧬 Supermemory Context</SectionLabel>
                  <span className="rounded-full border border-accent-primary/30 bg-accent-subtle px-2 py-0.5 text-xs font-medium text-accent-primary">
                    AI
                  </span>
                </div>
                <p className="mb-3 text-xs text-tertiary">
                  Semantically retrieved past decisions relevant to current critical issues.
                </p>
                <MemoryContextPanel context={data.memory_context} />
              </div>

              {/* ── semantic memory search ── */}
              <div className="mt-6 rounded-xl border border-subtle bg-surface-1 p-5">
                <SectionLabel>🔍 Semantic Memory Search</SectionLabel>
                <p className="mb-3 text-xs text-tertiary">
                  Search across all past signals, insights, specs, and decisions stored in Supermemory.
                </p>
                <form onSubmit={handleSearch} className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="e.g. dark mode, onboarding friction, mobile performance…"
                    className="flex-1 rounded-md border border-subtle bg-surface-2 px-3 py-2 text-sm text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={isSearching || !searchQuery.trim()}
                    className="flex items-center gap-1.5 rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
                  >
                    {isSearching ? <Spinner className="size-3.5" /> : null}
                    Search
                  </button>
                </form>

                {searchResults.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-xs text-tertiary">{searchResults.length} results:</p>
                    {searchResults.map((r: unknown, i) => {
                      const result = r as Record<string, unknown>;
                      const content =
                        (result.content as string) ||
                        (result.text as string) ||
                        JSON.stringify(r);
                      return (
                        <div
                          key={i}
                          className="rounded-lg border border-subtle bg-surface-2 px-4 py-3 text-xs text-secondary"
                        >
                          {content.slice(0, 400)}
                          {content.length > 400 && "…"}
                        </div>
                      );
                    })}
                  </div>
                )}

                {searchResults.length === 0 && searchQuery && !isSearching && (
                  <p className="mt-3 text-xs italic text-placeholder">
                    No results. Make sure SUPERMEMORY_API_KEY is set in your .env.
                  </p>
                )}
              </div>

              {/* ── ingestion stats footer ── */}
              <div className="mt-6 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-dashed border-subtle bg-surface-2 px-5 py-4 text-xs text-secondary">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-primary">{data.insights.total}</span>
                  <span>insights extracted</span>
                </div>
                <div className="hidden h-4 w-px bg-subtle sm:block" />
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-primary">{data.specs.total}</span>
                  <span>specs generated</span>
                </div>
                <div className="hidden h-4 w-px bg-subtle sm:block" />
                <a
                  href={`/${workspaceSlug}/signals`}
                  className="flex items-center gap-1.5 text-accent-primary hover:underline"
                >
                  <span>+ Add signals</span>
                  <svg className="size-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2 6h8M7 3l3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </a>
              </div>
            </>
          )}

          {/* empty state when no data and no error */}
          {!data && !isLoading && !error && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-subtle py-20 text-center">
              <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-surface-2 text-tertiary">
                <svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="mb-1 text-base font-medium text-secondary">No health data yet</p>
              <p className="max-w-xs text-sm text-tertiary">
                Start by adding signals, then generate insights and specs.
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
