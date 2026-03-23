import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router";

const API_BASE = "/api";

async function apiGet(url: string) {
  const res = await fetch(`${API_BASE}${url}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPost(url: string, body: Record<string, unknown> = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function downloadMarkdown(spec: any) {
  const j = spec.spec_json || {};
  let md = `# ${j.feature_name || spec.title}\n\n`;
  md += `## Problem\n${j.problem || ""}\n\n`;
  md += `## User Story\n${j.user_story || ""}\n\n`;
  md += `## Solution\n${j.solution || ""}\n\n`;
  if (j.ui_changes?.length) { md += `## UI Changes\n${(j.ui_changes as string[]).map((c) => `- ${c}`).join("\n")}\n\n`; }
  if (j.data_model_changes?.length) { md += `## Data Model\n${(j.data_model_changes as string[]).map((c) => `- ${c}`).join("\n")}\n\n`; }
  if (j.workflow_changes?.length) { md += `## Workflow\n${(j.workflow_changes as string[]).map((c) => `- ${c}`).join("\n")}\n\n`; }
  if (j.tasks?.length) {
    md += `## Agent Tasks\n\n`;
    (j.tasks as any[]).forEach((t, i) => {
      md += `### Task ${i + 1}\n<read_first>\n`;
      (t.read_first || []).forEach((f: string) => (md += `- ${f}\n`));
      md += `</read_first>\n<action>\n`;
      (t.action || []).forEach((a: string) => (md += `- ${a}\n`));
      md += `</action>\n\n`;
    });
  }
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${String(spec.title || "spec").replace(/\s+/g, "_")}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function WorkspaceSpecsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const [specs, setSpecs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSpecs = useCallback(async () => {
    if (!workspaceSlug) return;
    setIsLoading(true);
    try {
      const data = await apiGet(`/workspaces/${workspaceSlug}/specs/`);
      setSpecs(Array.isArray(data) ? data : data.results ?? []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    fetchSpecs();
  }, [fetchSpecs]);

  const handleGenerate = async () => {
    if (!workspaceSlug) return;
    setIsGenerating(true);
    try {
      await apiPost(`/workspaces/${workspaceSlug}/specs/generate/`);
      alert("✅ Spec generation queued based on your latest insights! Refreshing in 10 seconds...");
      setTimeout(() => fetchSpecs(), 10000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Generated AI Specs</h1>
          <p className="text-gray-500 mt-1">Structured execution plans ready for developers and AI agents.</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
        >
          {isGenerating ? "Generating..." : "🔥 Generate from Insights"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
          Error: {error}{" "}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-500">Loading specs...</p>
      ) : (
        <div className="space-y-8">
          {specs.map((spec) => {
            const j = spec.spec_json || {};
            return (
              <div key={spec.id} className="border p-6 rounded-xl shadow-sm bg-white">
                <div className="flex justify-between items-start mb-4 border-b pb-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{j.feature_name || spec.title}</h2>
                    <p className="text-xs text-gray-400 mt-1">Generated: {new Date(spec.created_at).toLocaleString()}</p>
                  </div>
                  <button
                    onClick={() => downloadMarkdown(spec)}
                    className="px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50 transition-colors"
                  >
                    ↓ Download .md
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                  <div>
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Problem</h3>
                    <p className="text-sm text-gray-800">{j.problem}</p>
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mt-4 mb-1">User Story</h3>
                    <p className="text-sm italic text-gray-700">{j.user_story}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Solution</h3>
                    <p className="text-sm text-gray-800">{j.solution}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mb-6">
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <span className="font-semibold text-blue-800 block mb-2 text-xs uppercase">UI Changes</span>
                    <ul className="list-disc pl-3 space-y-1 text-blue-900">
                      {((j.ui_changes || []) as string[]).map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                  <div className="bg-green-50 p-3 rounded-lg">
                    <span className="font-semibold text-green-800 block mb-2 text-xs uppercase">Data Model</span>
                    <ul className="list-disc pl-3 space-y-1 text-green-900">
                      {((j.data_model_changes || []) as string[]).map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg">
                    <span className="font-semibold text-purple-800 block mb-2 text-xs uppercase">Workflow</span>
                    <ul className="list-disc pl-3 space-y-1 text-purple-900">
                      {((j.workflow_changes || []) as string[]).map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                    Agent Tasks ({(j.tasks as any[] | undefined)?.length ?? 0})
                  </h3>
                  <div className="space-y-2">
                    {((j.tasks || []) as any[]).map((task, i) => (
                      <div key={i} className="bg-gray-50 p-3 rounded-lg text-xs font-mono border">
                        <div className="text-gray-400 mb-1">&lt;read_first&gt;</div>
                        <ul className="pl-3 text-orange-700 list-disc mb-2">
                          {((task.read_first || []) as string[]).map((f, fi) => <li key={fi}>{f}</li>)}
                        </ul>
                        <div className="text-gray-400 mb-1">&lt;action&gt;</div>
                        <ul className="pl-3 text-blue-700 list-disc">
                          {((task.action || []) as string[]).map((a, ai) => <li key={ai}>{a}</li>)}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}

          {specs.length === 0 && !isLoading && (
            <div className="text-center py-16 text-gray-400 border-2 border-dashed rounded-xl">
              <p className="text-lg mb-2">No specs yet</p>
              <p className="text-sm">Go to Insights → Generate Insights first, then come here and click &ldquo;Generate from Insights&rdquo;.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
