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

interface SpecTask {
  read_first: string[];
  action: string[];
}

interface SpecJson {
  feature_name?: string;
  problem?: string;
  user_story?: string;
  solution?: string;
  ui_changes?: string[];
  data_model_changes?: string[];
  workflow_changes?: string[];
  tasks?: SpecTask[];
}

interface SpecIssue {
  id: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "done" | "cancelled";
  assignee_email: string | null;
  created_at: string;
}

type ExecutionStatus =
  | "none"
  | "pending"
  | "generating"
  | "pr_created"
  | "pr_merged"
  | "failed";

interface Outcome {
  id: string;
  result: "success" | "partial" | "failure" | "inconclusive";
  success_score: number;
  metrics_before: Record<string, unknown>;
  metrics_after: Record<string, unknown>;
  notes: string | null;
  pr_url: string | null;
  created_at: string;
}

interface GeneratedSpec {
  id: string;
  title: string;
  spec_json: SpecJson;
  agent_payload: Record<string, unknown>;
  status: "proposed" | "in_progress" | "completed" | "rejected";
  issues: SpecIssue[];
  // Prioritization Engine v2
  impact_score: number;
  effort_score: number;
  priority_score: number;
  confidence_score: number;
  recency_weight: number;
  risk_score: number;
  // Execution tracking
  execution_status: ExecutionStatus;
  github_pr_url: string | null;
  github_branch: string | null;
  execution_log: unknown[];
  // Outcome
  outcome: Outcome | null;
  created_at: string;
}

// ─── constants ────────────────────────────────────────────────────────────────

const SPEC_STATUS_CONFIG: Record<
  GeneratedSpec["status"],
  { label: string; bg: string; text: string; dot: string }
> = {
  proposed: {
    label: "Proposed",
    bg: "bg-surface-2",
    text: "text-secondary",
    dot: "bg-tertiary",
  },
  in_progress: {
    label: "In Progress",
    bg: "bg-accent-subtle",
    text: "text-accent-primary",
    dot: "bg-accent-primary",
  },
  completed: {
    label: "Completed",
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-700 dark:text-green-400",
    dot: "bg-green-500",
  },
  rejected: {
    label: "Rejected",
    bg: "bg-red-100 dark:bg-red-900/30",
    text: "text-red-700 dark:text-red-400",
    dot: "bg-red-500",
  },
};

const ISSUE_STATUS_CONFIG: Record<
  SpecIssue["status"],
  { label: string; bg: string; text: string }
> = {
  todo: { label: "To Do", bg: "bg-surface-2", text: "text-secondary" },
  in_progress: {
    label: "In Progress",
    bg: "bg-accent-subtle",
    text: "text-accent-primary",
  },
  done: {
    label: "Done",
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-700 dark:text-green-400",
  },
  cancelled: {
    label: "Cancelled",
    bg: "bg-red-100 dark:bg-red-900/30",
    text: "text-red-600 dark:text-red-400",
  },
};

// ─── small components ─────────────────────────────────────────────────────────

function SpecStatusBadge({ status }: { status: GeneratedSpec["status"] }) {
  const cfg = SPEC_STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}
    >
      <span className={`size-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function IssueBadge({ status }: { status: SpecIssue["status"] }) {
  const cfg = ISSUE_STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.text}`}
    >
      {cfg.label}
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-tertiary">
      {children}
    </p>
  );
}

function BulletList({
  items,
  colorClass,
}: {
  items: string[];
  colorClass: string;
}) {
  if (!items.length)
    return <p className="text-xs italic text-placeholder">None specified</p>;
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li
          key={i}
          className={`flex items-start gap-1.5 text-sm ${colorClass}`}
        >
          <span className="mt-1.5 size-1.5 flex-shrink-0 rounded-full bg-current opacity-60" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function Spinner({ className = "size-4" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
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
  );
}

// ─── download helper ──────────────────────────────────────────────────────────

function downloadMarkdown(spec: GeneratedSpec) {
  const j = spec.spec_json;
  let md = `# ${j.feature_name ?? spec.title}\n\n`;
  md += `**Status:** ${spec.status}\n\n`;
  md += `## Problem\n${j.problem ?? ""}\n\n`;
  md += `## User Story\n${j.user_story ?? ""}\n\n`;
  md += `## Solution\n${j.solution ?? ""}\n\n`;
  if (j.ui_changes?.length)
    md += `## UI Changes\n${j.ui_changes.map((c) => `- ${c}`).join("\n")}\n\n`;
  if (j.data_model_changes?.length)
    md += `## Data Model\n${j.data_model_changes.map((c) => `- ${c}`).join("\n")}\n\n`;
  if (j.workflow_changes?.length)
    md += `## Workflow\n${j.workflow_changes.map((c) => `- ${c}`).join("\n")}\n\n`;
  if (j.tasks?.length) {
    md += `## Agent Tasks\n\n`;
    j.tasks.forEach((t, i) => {
      md += `### Task ${i + 1}\n<read_first>\n`;
      (t.read_first ?? []).forEach((f) => (md += `- ${f}\n`));
      md += `</read_first>\n<action>\n`;
      (t.action ?? []).forEach((a) => (md += `- ${a}\n`));
      md += `</action>\n\n`;
    });
  }
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${String(j.feature_name ?? spec.title).replace(/\s+/g, "_")}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

// ─── sub-sections ─────────────────────────────────────────────────────────────

function AgentPayloadPanel({
  spec,
  workspaceSlug,
  onPayloadGenerated,
}: {
  spec: GeneratedSpec;
  workspaceSlug: string;
  onPayloadGenerated: (payload: Record<string, unknown>) => void;
}) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const payload = spec.agent_payload;
  const hasPayload = payload && Object.keys(payload).length > 0;

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/specs/${spec.id}/agent-payload/`,
        { method: "POST", body: JSON.stringify({}) },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      onPayloadGenerated(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate payload");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!hasPayload) return;
    const prompt =
      (payload.prompt as string) ?? JSON.stringify(payload, null, 2);
    copyToClipboard(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-subtle bg-surface-2 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <SectionLabel>Coding Agent Prompt</SectionLabel>
          <p className="text-xs text-tertiary">
            Structured prompt for Cursor, Claude Code, or any AI coding agent.
          </p>
        </div>
        <div className="flex gap-2">
          {hasPayload && (
            <button
              onClick={handleCopy}
              className="rounded-md border border-subtle px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-1 transition-colors"
            >
              {copied ? "✓ Copied" : "Copy prompt"}
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="rounded-md bg-accent-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
          >
            {isGenerating ? (
              <span className="flex items-center gap-1.5">
                <Spinner className="size-3" />
                Generating…
              </span>
            ) : hasPayload ? (
              "Regenerate"
            ) : (
              "Send to Coding Agent"
            )}
          </button>
        </div>
      </div>
      {error && <p className="mb-2 text-xs text-danger-primary">{error}</p>}
      {hasPayload && (
        <div className="max-h-48 overflow-y-auto rounded-lg border border-subtle bg-surface-1 p-3 font-mono text-xs text-secondary">
          <pre className="whitespace-pre-wrap break-words">
            {(payload.prompt as string) ?? JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ─── Execution Panel ──────────────────────────────────────────────────────────

const EXECUTION_STATUS_CONFIG: Record<
  ExecutionStatus,
  { label: string; bg: string; text: string; icon: string }
> = {
  none: {
    label: "Not executed",
    bg: "bg-surface-2",
    text: "text-secondary",
    icon: "○",
  },
  pending: {
    label: "Queued",
    bg: "bg-accent-subtle",
    text: "text-accent-primary",
    icon: "⏳",
  },
  generating: {
    label: "Generating code…",
    bg: "bg-amber-100 dark:bg-amber-900/30",
    text: "text-amber-700 dark:text-amber-400",
    icon: "⚡",
  },
  pr_created: {
    label: "PR Created",
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-700 dark:text-green-400",
    icon: "✓",
  },
  pr_merged: {
    label: "PR Merged",
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-700 dark:text-green-400",
    icon: "✅",
  },
  failed: {
    label: "Failed",
    bg: "bg-red-100 dark:bg-red-900/30",
    text: "text-red-700 dark:text-red-400",
    icon: "✗",
  },
};

function ExecutionStatusBadge({ status }: { status: ExecutionStatus }) {
  const cfg = EXECUTION_STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}
    >
      <span>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

function ExecutionPanel({
  spec,
  workspaceSlug,
  onExecutionStarted,
}: {
  spec: GeneratedSpec;
  workspaceSlug: string;
  onExecutionStarted: (specId: string, status: ExecutionStatus) => void;
}) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = async () => {
    if (isExecuting) return;
    setIsExecuting(true);
    setError(null);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/specs/${spec.id}/execute/`,
        { method: "POST", body: JSON.stringify({}) },
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error ?? `HTTP ${res.status}`);
      }
      onExecutionStarted(spec.id, "pending");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Execution failed");
    } finally {
      setIsExecuting(false);
    }
  };

  const canExecute = !["pending", "generating"].includes(spec.execution_status);
  const cfg = EXECUTION_STATUS_CONFIG[spec.execution_status];

  return (
    <div className="rounded-xl border border-subtle bg-surface-2 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <SectionLabel>GitHub Execution</SectionLabel>
          <p className="text-xs text-tertiary">
            Generate code, create a branch, and open a Pull Request
            automatically.
          </p>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <ExecutionStatusBadge status={spec.execution_status} />
          {canExecute && (
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {isExecuting ? (
                <>
                  <svg
                    className="size-3 animate-spin"
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
                  Queuing…
                </>
              ) : (
                <>
                  <svg
                    className="size-3"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M5 3l7 4-7 4V3z" strokeLinejoin="round" />
                  </svg>
                  {spec.execution_status === "failed"
                    ? "Retry"
                    : "Execute Spec"}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {error && (
        <p className="mb-2 rounded-md bg-danger-subtle px-3 py-2 text-xs text-danger-primary">
          {error}
        </p>
      )}

      {/* PR link */}
      {spec.github_pr_url && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2 dark:border-green-800 dark:bg-green-900/20">
          <svg
            className="size-3.5 text-green-600 dark:text-green-400 flex-shrink-0"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z" />
          </svg>
          <a
            href={spec.github_pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-green-700 underline dark:text-green-400 truncate"
          >
            {spec.github_pr_url}
          </a>
        </div>
      )}

      {/* Branch name */}
      {spec.github_branch && (
        <p className="mt-2 text-xs text-tertiary">
          Branch:{" "}
          <code className="rounded bg-surface-1 px-1.5 py-0.5 font-mono text-secondary">
            {spec.github_branch}
          </code>
        </p>
      )}

      {/* Config hint */}
      {spec.execution_status === "none" && !spec.github_pr_url && (
        <p className="mt-2 text-xs text-placeholder">
          Requires <code className="font-mono">GITHUB_TOKEN</code>,{" "}
          <code className="font-mono">GITHUB_REPO_OWNER</code>,{" "}
          <code className="font-mono">GITHUB_REPO_NAME</code> in your{" "}
          <code className="font-mono">.env</code>.
        </p>
      )}
    </div>
  );
}

// ─── Outcome Panel ────────────────────────────────────────────────────────────

function OutcomePanel({
  spec,
  workspaceSlug,
  onOutcomeRecorded,
}: {
  spec: GeneratedSpec;
  workspaceSlug: string;
  onOutcomeRecorded: (specId: string, outcome: Outcome) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    result: "success" as Outcome["result"],
    success_score: 0.8,
    notes: "",
    metrics_before: "",
    metrics_after: "",
  });

  const handleRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      let mb: Record<string, unknown> = {};
      let ma: Record<string, unknown> = {};
      try {
        mb = form.metrics_before ? JSON.parse(form.metrics_before) : {};
      } catch {
        mb = { raw: form.metrics_before };
      }
      try {
        ma = form.metrics_after ? JSON.parse(form.metrics_after) : {};
      } catch {
        ma = { raw: form.metrics_after };
      }

      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/outcomes/record/`,
        {
          method: "POST",
          body: JSON.stringify({
            spec_id: spec.id,
            result: form.result,
            success_score: form.success_score,
            notes: form.notes,
            metrics_before: mb,
            metrics_after: ma,
          }),
        },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      // Optimistically update
      onOutcomeRecorded(spec.id, {
        id: "pending",
        result: form.result,
        success_score: form.success_score,
        metrics_before: mb,
        metrics_after: ma,
        notes: form.notes,
        pr_url: spec.github_pr_url,
        created_at: new Date().toISOString(),
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to record outcome");
    } finally {
      setIsSubmitting(false);
    }
  };

  const RESULT_CONFIG: Record<
    string,
    { label: string; bg: string; text: string }
  > = {
    success: {
      label: "✅ Success",
      bg: "bg-green-100 dark:bg-green-900/30",
      text: "text-green-700 dark:text-green-400",
    },
    partial: {
      label: "⚠️ Partial",
      bg: "bg-amber-100 dark:bg-amber-900/30",
      text: "text-amber-700 dark:text-amber-400",
    },
    failure: {
      label: "❌ Failure",
      bg: "bg-red-100 dark:bg-red-900/30",
      text: "text-red-700 dark:text-red-400",
    },
    inconclusive: {
      label: "❓ Inconclusive",
      bg: "bg-surface-2",
      text: "text-secondary",
    },
  };

  const existingOutcome = spec.outcome;

  return (
    <div className="rounded-xl border border-subtle bg-surface-2 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <SectionLabel>Outcome Tracking</SectionLabel>
          <p className="text-xs text-tertiary">
            Record what happened after this feature shipped. Feeds the learning
            loop.
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex-shrink-0 rounded-md border border-subtle px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-1 transition-colors"
          >
            {existingOutcome ? "Update" : "Record Outcome"}
          </button>
        )}
      </div>

      {/* Existing outcome display */}
      {existingOutcome && !showForm && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${RESULT_CONFIG[existingOutcome.result]?.bg} ${RESULT_CONFIG[existingOutcome.result]?.text}`}
            >
              {RESULT_CONFIG[existingOutcome.result]?.label ??
                existingOutcome.result}
            </span>
            <span className="text-xs text-secondary">
              Score:{" "}
              <strong>
                {(existingOutcome.success_score * 100).toFixed(0)}%
              </strong>
            </span>
          </div>
          {existingOutcome.notes && (
            <p className="text-xs text-secondary">{existingOutcome.notes}</p>
          )}
          {Object.keys(existingOutcome.metrics_after ?? {}).length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(
                existingOutcome.metrics_after as Record<string, unknown>,
              ).map(([k, v]) => {
                const before = (
                  existingOutcome.metrics_before as Record<string, unknown>
                )?.[k];
                const isImproved =
                  before !== undefined && Number(v) < Number(before);
                return (
                  <div
                    key={k}
                    className="rounded-lg border border-subtle bg-surface-1 px-3 py-2"
                  >
                    <p className="text-xs text-placeholder capitalize">
                      {k.replace(/_/g, " ")}
                    </p>
                    <p className="text-sm font-semibold text-primary">
                      {String(v)}
                      {before !== undefined && (
                        <span
                          className={`ml-1.5 text-xs ${isImproved ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
                        >
                          ({isImproved ? "↓" : "↑"} from {String(before)})
                        </span>
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
          <p className="text-xs text-placeholder">
            Recorded {new Date(existingOutcome.created_at).toLocaleDateString()}
          </p>
        </div>
      )}

      {/* Record form */}
      {showForm && (
        <form onSubmit={handleRecord} className="space-y-3">
          {error && (
            <p className="rounded bg-danger-subtle px-3 py-2 text-xs text-danger-primary">
              {error}
            </p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-secondary">
                Result
              </label>
              <select
                value={form.result}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    result: e.target.value as Outcome["result"],
                  }))
                }
                className="w-full rounded-md border border-subtle bg-surface-1 px-2 py-1.5 text-xs text-primary focus:outline-none"
              >
                <option value="success">Success</option>
                <option value="partial">Partial Success</option>
                <option value="failure">Failure</option>
                <option value="inconclusive">Inconclusive</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-secondary">
                Success Score ({Math.round(form.success_score * 100)}%)
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={form.success_score}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    success_score: parseFloat(e.target.value),
                  }))
                }
                className="w-full accent-accent-primary"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-secondary">
              Metrics Before{" "}
              <span className="text-placeholder">
                (JSON, e.g. {'{ "bug_reports": 12 }'})
              </span>
            </label>
            <input
              value={form.metrics_before}
              onChange={(e) =>
                setForm((f) => ({ ...f, metrics_before: e.target.value }))
              }
              placeholder='{ "bug_reports": 12, "churn_rate": 0.05 }'
              className="w-full rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-xs font-mono text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-secondary">
              Metrics After
            </label>
            <input
              value={form.metrics_after}
              onChange={(e) =>
                setForm((f) => ({ ...f, metrics_after: e.target.value }))
              }
              placeholder='{ "bug_reports": 3, "churn_rate": 0.02 }'
              className="w-full rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-xs font-mono text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-secondary">
              Notes
            </label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) =>
                setForm((f) => ({ ...f, notes: e.target.value }))
              }
              placeholder="What happened? What did users say? Did it solve the problem?"
              className="w-full rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-xs text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setError(null);
              }}
              className="rounded-md border border-subtle px-3 py-1.5 text-xs font-medium text-secondary hover:bg-surface-1 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md bg-accent-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? "Recording…" : "Record & Learn"}
            </button>
          </div>
        </form>
      )}

      {/* Empty state */}
      {!existingOutcome && !showForm && (
        <p className="text-xs italic text-placeholder">
          No outcome recorded yet. Record one after the feature ships to train
          the system.
        </p>
      )}
    </div>
  );
}

function IssueList({
  spec,
  workspaceSlug,
  onIssueUpdated,
}: {
  spec: GeneratedSpec;
  workspaceSlug: string;
  onIssueUpdated: (specId: string, issues: SpecIssue[]) => void;
}) {
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    assignee_email: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const defaultTitle = spec.spec_json.feature_name ?? spec.title;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    setError(null);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/specs/${spec.id}/create-issue/`,
        {
          method: "POST",
          body: JSON.stringify({
            title: form.title || defaultTitle,
            description: form.description,
            assignee_email: form.assignee_email || undefined,
          }),
        },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const newIssue: SpecIssue = await res.json();
      onIssueUpdated(spec.id, [...spec.issues, newIssue]);
      setShowForm(false);
      setForm({ title: "", description: "", assignee_email: "" });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create issue");
    } finally {
      setIsCreating(false);
    }
  };

  const handleStatusChange = async (
    issue: SpecIssue,
    newStatus: SpecIssue["status"],
  ) => {
    setUpdatingId(issue.id);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/specs/${spec.id}/issues/${issue.id}/status/`,
        { method: "PATCH", body: JSON.stringify({ status: newStatus }) },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const updated: SpecIssue = await res.json();
      onIssueUpdated(
        spec.id,
        spec.issues.map((i) => (i.id === updated.id ? updated : i)),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update issue");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <SectionLabel>Issues ({spec.issues.length})</SectionLabel>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-md px-2.5 py-1 text-xs font-medium text-accent-primary hover:bg-accent-subtle transition-colors"
        >
          {showForm ? "Cancel" : "+ Create Issue"}
        </button>
      </div>

      {error && <p className="mb-2 text-xs text-danger-primary">{error}</p>}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-3 rounded-lg border border-subtle bg-surface-2 p-3 space-y-2"
        >
          <input
            className="w-full rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-xs text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
            placeholder={`Issue title (default: "${defaultTitle}")`}
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          />
          <input
            className="w-full rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-xs text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
            placeholder="Assignee email (optional)"
            type="email"
            value={form.assignee_email}
            onChange={(e) =>
              setForm((f) => ({ ...f, assignee_email: e.target.value }))
            }
          />
          <textarea
            rows={2}
            className="w-full rounded-md border border-subtle bg-surface-1 px-3 py-1.5 text-xs text-primary placeholder:text-placeholder focus:border-accent-primary focus:outline-none"
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) =>
              setForm((f) => ({ ...f, description: e.target.value }))
            }
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded px-2.5 py-1 text-xs text-secondary hover:bg-surface-1 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="rounded bg-accent-primary px-2.5 py-1 text-xs font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
            >
              {isCreating ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      )}

      {spec.issues.length === 0 && !showForm ? (
        <p className="text-xs italic text-placeholder py-2">
          No issues yet. Create one to start tracking execution.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {spec.issues.map((issue) => (
            <li
              key={issue.id}
              className="flex items-start gap-3 rounded-lg border border-subtle bg-surface-1 px-3 py-2"
            >
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-primary truncate">
                  {issue.title}
                </p>
                {issue.assignee_email && (
                  <p className="text-xs text-tertiary">
                    {issue.assignee_email}
                  </p>
                )}
              </div>
              <div className="flex flex-shrink-0 items-center gap-2">
                {updatingId === issue.id ? (
                  <Spinner className="size-3 text-tertiary" />
                ) : (
                  <select
                    value={issue.status}
                    onChange={(e) =>
                      handleStatusChange(
                        issue,
                        e.target.value as SpecIssue["status"],
                      )
                    }
                    className="rounded border border-subtle bg-surface-2 px-1.5 py-0.5 text-xs text-primary focus:outline-none cursor-pointer"
                  >
                    <option value="todo">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                )}
                <IssueBadge status={issue.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── spec card ────────────────────────────────────────────────────────────────

function SpecCard({
  spec,
  workspaceSlug,
  onDelete,
  onStatusChange,
  onIssueUpdated,
  onPayloadGenerated,
  onExecutionStarted,
  onOutcomeRecorded,
}: {
  spec: GeneratedSpec;
  workspaceSlug: string;
  onDelete: (id: string) => void;
  onStatusChange: (id: string, status: GeneratedSpec["status"]) => void;
  onIssueUpdated: (specId: string, issues: SpecIssue[]) => void;
  onPayloadGenerated: (
    specId: string,
    payload: Record<string, unknown>,
  ) => void;
  onExecutionStarted: (specId: string, status: ExecutionStatus) => void;
  onOutcomeRecorded: (specId: string, outcome: Outcome) => void;
}) {
  const j = spec.spec_json;
  const tasks = j.tasks ?? [];
  const [isChangingStatus, setIsChangingStatus] = useState(false);
  const [expanded, setExpanded] = useState(true);

  // priority display
  const hasPriority = spec.priority_score > 0;

  const handleStatusChange = async (newStatus: GeneratedSpec["status"]) => {
    setIsChangingStatus(true);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/specs/${spec.id}/status/`,
        { method: "PATCH", body: JSON.stringify({ status: newStatus }) },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onStatusChange(spec.id, newStatus);
    } catch {
      // silently ignore
    } finally {
      setIsChangingStatus(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-subtle bg-surface-1 shadow-sm transition-shadow hover:shadow-md">
      {/* ── card header ── */}
      <div className="flex items-start justify-between gap-4 border-b border-subtle bg-surface-2 px-5 py-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <SpecStatusBadge status={spec.status} />
            <ExecutionStatusBadge status={spec.execution_status} />
            <h2 className="text-sm font-semibold text-primary truncate">
              {j.feature_name ?? spec.title}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3 mt-0.5">
            <p className="text-xs text-tertiary">
              Created {new Date(spec.created_at).toLocaleString()}
            </p>
            {hasPriority && (
              <span className="flex items-center gap-1 text-xs text-secondary">
                <span className="text-placeholder">Priority</span>
                <span className="font-semibold text-accent-primary">
                  {spec.priority_score.toFixed(2)}
                </span>
                <span className="text-placeholder">
                  · Impact {spec.impact_score.toFixed(1)}
                </span>
                <span className="text-placeholder">
                  · Effort {spec.effort_score.toFixed(1)}
                </span>
                {spec.risk_score !== 1.0 && (
                  <span className="text-placeholder">
                    · Risk {spec.risk_score.toFixed(2)}
                  </span>
                )}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-shrink-0 items-center gap-2">
          {/* Status selector */}
          {isChangingStatus ? (
            <Spinner className="size-4 text-tertiary" />
          ) : (
            <select
              value={spec.status}
              onChange={(e) =>
                handleStatusChange(e.target.value as GeneratedSpec["status"])
              }
              className="rounded-md border border-subtle bg-surface-1 px-2 py-1 text-xs text-secondary focus:outline-none cursor-pointer hover:bg-surface-2 transition-colors"
            >
              <option value="proposed">Proposed</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="rejected">Rejected</option>
            </select>
          )}

          {/* Download */}
          <button
            onClick={() => downloadMarkdown(spec)}
            className="flex items-center gap-1 rounded-md border border-subtle px-2.5 py-1 text-xs font-medium text-secondary hover:bg-surface-2 transition-colors"
            title="Download .md"
          >
            <svg
              className="size-3"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                d="M8 2v9M4 8l4 4 4-4M2 13h12"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            .md
          </button>

          {/* Collapse */}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded-md p-1.5 text-tertiary hover:bg-surface-2 transition-colors"
            title={expanded ? "Collapse" : "Expand"}
          >
            <svg
              className={`size-4 transition-transform ${expanded ? "rotate-180" : ""}`}
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                d="M4 6l4 4 4-4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          {/* Delete */}
          <button
            onClick={() => onDelete(spec.id)}
            className="rounded-md p-1.5 text-tertiary hover:bg-danger-subtle hover:text-danger-primary transition-colors"
            title="Delete spec"
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
        </div>
      </div>

      {/* ── expandable body ── */}
      {expanded && (
        <div className="px-5 py-5 space-y-6">
          {/* problem + story + solution */}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <div className="space-y-4">
              {j.problem && (
                <div>
                  <SectionLabel>Problem</SectionLabel>
                  <p className="text-sm text-primary">{j.problem}</p>
                </div>
              )}
              {j.user_story && (
                <div>
                  <SectionLabel>User Story</SectionLabel>
                  <p className="text-sm italic text-secondary">
                    {j.user_story}
                  </p>
                </div>
              )}
            </div>
            {j.solution && (
              <div>
                <SectionLabel>Solution</SectionLabel>
                <p className="text-sm text-primary">{j.solution}</p>
              </div>
            )}
          </div>

          {/* change columns */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-subtle bg-accent-subtle/40 p-4">
              <SectionLabel>UI Changes</SectionLabel>
              <BulletList
                items={j.ui_changes ?? []}
                colorClass="text-accent-primary"
              />
            </div>
            <div className="rounded-lg border border-subtle bg-success-subtle/40 p-4">
              <SectionLabel>Data Model</SectionLabel>
              <BulletList
                items={j.data_model_changes ?? []}
                colorClass="text-success-primary"
              />
            </div>
            <div className="rounded-lg border border-subtle bg-surface-2 p-4">
              <SectionLabel>Workflow</SectionLabel>
              <BulletList
                items={j.workflow_changes ?? []}
                colorClass="text-secondary"
              />
            </div>
          </div>

          {/* agent tasks */}
          {tasks.length > 0 && (
            <div>
              <SectionLabel>Agent Tasks ({tasks.length})</SectionLabel>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {tasks.map((task, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-subtle bg-surface-2 p-3 font-mono text-xs"
                  >
                    <div className="mb-1 text-tertiary">&lt;read_first&gt;</div>
                    <ul className="mb-2 space-y-0.5 pl-3">
                      {(task.read_first ?? []).map((f, fi) => (
                        <li
                          key={fi}
                          className="text-amber-600 dark:text-amber-400"
                        >
                          — {f}
                        </li>
                      ))}
                    </ul>
                    <div className="mb-1 text-tertiary">&lt;action&gt;</div>
                    <ul className="space-y-0.5 pl-3">
                      {(task.action ?? []).map((a, ai) => (
                        <li key={ai} className="text-accent-primary">
                          — {a}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-1.5 text-placeholder">Task {i + 1}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* issues */}
          <div className="border-t border-subtle pt-5">
            <IssueList
              spec={spec}
              workspaceSlug={workspaceSlug}
              onIssueUpdated={onIssueUpdated}
            />
          </div>

          {/* agent payload */}
          <AgentPayloadPanel
            spec={spec}
            workspaceSlug={workspaceSlug}
            onPayloadGenerated={(payload) =>
              onPayloadGenerated(spec.id, payload)
            }
          />

          {/* execution agent */}
          <ExecutionPanel
            spec={spec}
            workspaceSlug={workspaceSlug}
            onExecutionStarted={onExecutionStarted}
          />

          {/* outcome tracking */}
          <OutcomePanel
            spec={spec}
            workspaceSlug={workspaceSlug}
            onOutcomeRecorded={onOutcomeRecorded}
          />
        </div>
      )}
    </div>
  );
}

// ─── dashboard summary ────────────────────────────────────────────────────────

function StatusDashboard({ specs }: { specs: GeneratedSpec[] }) {
  const counts = specs.reduce<Record<string, number>>(
    (acc, s) => ({ ...acc, [s.status]: (acc[s.status] ?? 0) + 1 }),
    {},
  );
  const tiles: Array<{ key: GeneratedSpec["status"]; icon: string }> = [
    { key: "proposed", icon: "💡" },
    { key: "in_progress", icon: "⚡" },
    { key: "completed", icon: "✅" },
    { key: "rejected", icon: "✗" },
  ];
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map(({ key, icon }) => {
        const cfg = SPEC_STATUS_CONFIG[key];
        const count = counts[key] ?? 0;
        return (
          <div
            key={key}
            className={`flex items-center gap-3 rounded-xl border border-subtle p-4 ${cfg.bg}`}
          >
            <span className="text-lg">{icon}</span>
            <div>
              <p className={`text-xl font-bold ${cfg.text}`}>{count}</p>
              <p className="text-xs text-secondary">{cfg.label}</p>
            </div>
          </div>
        );
      })}
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
  ];
  return (
    <div className="mb-6 flex flex-wrap items-center gap-1 rounded-lg border border-subtle bg-surface-2 px-4 py-2 text-xs">
      {steps.map((step, i) => (
        <React.Fragment key={step.label}>
          <a
            href={step.href}
            className={`flex items-center gap-1.5 rounded-md px-2 py-1 font-medium transition-colors hover:bg-surface-1 ${
              step.label === "Specs"
                ? "bg-accent-primary text-white"
                : "text-secondary hover:text-primary"
            }`}
          >
            <span>{step.icon}</span>
            {step.label}
          </a>
          {i < steps.length - 1 && (
            <svg
              className="size-3 text-placeholder"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                d="M6 4l4 4-4 4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// ─── filter bar ──────────────────────────────────────────────────────────────

type StatusFilter = "all" | GeneratedSpec["status"];

function FilterBar({
  active,
  onChange,
  counts,
}: {
  active: StatusFilter;
  onChange: (v: StatusFilter) => void;
  counts: Record<string, number>;
}) {
  const tabs: Array<{ value: StatusFilter; label: string }> = [
    {
      value: "all",
      label: `All (${Object.values(counts).reduce((a, b) => a + b, 0)})`,
    },
    { value: "proposed", label: `Proposed (${counts.proposed ?? 0})` },
    { value: "in_progress", label: `In Progress (${counts.in_progress ?? 0})` },
    { value: "completed", label: `Completed (${counts.completed ?? 0})` },
    { value: "rejected", label: `Rejected (${counts.rejected ?? 0})` },
  ];
  return (
    <div className="mb-5 flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            active === tab.value
              ? "bg-accent-primary text-white"
              : "border border-subtle bg-surface-2 text-secondary hover:bg-surface-1"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function WorkspaceSpecsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  const [specs, setSpecs] = useState<GeneratedSpec[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  // ── fetch ──────────────────────────────────────────────────────────────────
  const fetchSpecs = useCallback(async () => {
    if (!workspaceSlug || typeof window === "undefined") return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/workspaces/${workspaceSlug}/specs/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSpecs(Array.isArray(data) ? data : (data.results ?? []));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load specs");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    fetchSpecs();
  }, [fetchSpecs]);

  // ── generate ───────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!workspaceSlug || isGenerating) return;
    setIsGenerating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await apiFetch(
        `/api/workspaces/${workspaceSlug}/specs/generate/`,
        { method: "POST", body: JSON.stringify({}) },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      setSuccessMsg("🔥 Spec generation queued! Refreshing in 12s…");
      let secs = 12;
      setCountdown(secs);
      const tick = setInterval(() => {
        secs -= 1;
        setCountdown(secs);
        if (secs <= 0) {
          clearInterval(tick);
          setCountdown(null);
          setSuccessMsg(null);
          fetchSpecs();
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
        `/api/workspaces/${workspaceSlug}/specs/${id}/`,
        {
          method: "DELETE",
        },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSpecs((prev) => prev.filter((s) => s.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete spec");
    }
  };

  // ── local updates (no refetch needed) ─────────────────────────────────────
  const handleStatusChange = (
    id: string,
    newStatus: GeneratedSpec["status"],
  ) => {
    setSpecs((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: newStatus } : s)),
    );
  };

  const handleIssueUpdated = (specId: string, issues: SpecIssue[]) => {
    setSpecs((prev) =>
      prev.map((s) => (s.id === specId ? { ...s, issues } : s)),
    );
  };

  const handlePayloadGenerated = (
    specId: string,
    payload: Record<string, unknown>,
  ) => {
    setSpecs((prev) =>
      prev.map((s) => (s.id === specId ? { ...s, agent_payload: payload } : s)),
    );
  };

  const handleExecutionStarted = (specId: string, status: ExecutionStatus) => {
    setSpecs((prev) =>
      prev.map((s) =>
        s.id === specId ? { ...s, execution_status: status } : s,
      ),
    );
  };

  const handleOutcomeRecorded = (specId: string, outcome: Outcome) => {
    setSpecs((prev) =>
      prev.map((s) => (s.id === specId ? { ...s, outcome } : s)),
    );
  };

  // ── filter ─────────────────────────────────────────────────────────────────
  const filteredSpecs =
    statusFilter === "all"
      ? specs
      : specs.filter((s) => s.status === statusFilter);

  const statusCounts = specs.reduce<Record<string, number>>(
    (acc, s) => ({ ...acc, [s.status]: (acc[s.status] ?? 0) + 1 }),
    {},
  );

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="relative h-full w-full overflow-hidden overflow-y-auto">
      <div>
        <div className="mx-auto max-w-5xl px-6 py-8">
          {/* lifecycle nav */}
          {workspaceSlug && (
            <LifecycleBreadcrumb workspaceSlug={workspaceSlug} />
          )}

          {/* page header */}
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-primary">AI Specs</h1>
              <p className="mt-1 text-sm text-secondary">
                Structured execution plans. Track status, create issues, and
                send to your coding agent.
              </p>
            </div>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex-shrink-0 rounded-md bg-accent-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {isGenerating ? (
                <span className="flex items-center gap-2">
                  <Spinner className="size-3.5" />
                  Generating…
                </span>
              ) : (
                "🔥 Generate from Insights"
              )}
            </button>
          </div>

          {/* error */}
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

          {/* success */}
          {successMsg && (
            <div className="mb-4 flex items-center justify-between rounded-md border border-green-200 bg-success-subtle/60 px-4 py-3 text-sm text-success-primary dark:border-green-800">
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

          {/* dashboard */}
          {specs.length > 0 && <StatusDashboard specs={specs} />}

          {/* filter bar */}
          {specs.length > 0 && (
            <FilterBar
              active={statusFilter}
              onChange={setStatusFilter}
              counts={statusCounts}
            />
          )}

          {/* loading */}
          {isLoading && specs.length === 0 && (
            <div className="flex items-center justify-center py-20 text-sm text-tertiary">
              <Spinner className="mr-2 size-4" />
              Loading specs…
            </div>
          )}

          {/* spec list */}
          {!isLoading && filteredSpecs.length > 0 && (
            <div className="space-y-5">
              {filteredSpecs.map((spec) => (
                <SpecCard
                  key={spec.id}
                  spec={spec}
                  workspaceSlug={workspaceSlug ?? ""}
                  onDelete={handleDelete}
                  onStatusChange={handleStatusChange}
                  onIssueUpdated={handleIssueUpdated}
                  onPayloadGenerated={handlePayloadGenerated}
                  onExecutionStarted={handleExecutionStarted}
                  onOutcomeRecorded={handleOutcomeRecorded}
                />
              ))}
            </div>
          )}

          {/* empty — after filter */}
          {!isLoading && specs.length > 0 && filteredSpecs.length === 0 && (
            <div className="rounded-xl border-2 border-dashed border-subtle py-12 text-center">
              <p className="text-sm text-secondary">
                No specs with status{" "}
                <span className="font-semibold">{statusFilter}</span>.
              </p>
              <button
                onClick={() => setStatusFilter("all")}
                className="mt-3 text-xs text-accent-primary underline"
              >
                Show all specs
              </button>
            </div>
          )}

          {/* empty — no specs at all */}
          {!isLoading && specs.length === 0 && (
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
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <p className="mb-1 text-base font-medium text-secondary">
                No specs yet
              </p>
              <p className="max-w-xs text-sm text-tertiary">
                Go to{" "}
                <a
                  href={`/${workspaceSlug}/insights`}
                  className="font-medium text-accent-primary underline"
                >
                  Insights
                </a>{" "}
                first, generate insights, then come back to generate specs.
              </p>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="mt-5 rounded-md bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-50 transition-colors"
              >
                🔥 Generate from Insights
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
