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

export default function WorkspaceInsightsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const [insights, setInsights] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInsights = useCallback(async () => {
    if (!workspaceSlug) return;
    setIsLoading(true);
    try {
      const data = await apiGet(`/workspaces/${workspaceSlug}/insights/`);
      setInsights(Array.isArray(data) ? data : data.results ?? []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  const handleGenerate = async () => {
    if (!workspaceSlug) return;
    setIsGenerating(true);
    try {
      await apiPost(`/workspaces/${workspaceSlug}/signals/generate/`);
      alert("✅ Insight generation queued! Refreshing in 8 seconds...");
      setTimeout(() => fetchInsights(), 8000);
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
          <h1 className="text-2xl font-bold">AI Insights</h1>
          <p className="text-gray-500 mt-1">Recurring themes and root causes extracted from raw signals.</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
        >
          {isGenerating ? "Generating..." : "⚡ Generate Insights"}
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

      {isLoading ? (
        <p className="text-gray-500">Loading insights...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {insights.map((insight) => (
            <div key={insight.id} className="border p-5 rounded-xl shadow-sm flex flex-col gap-3 bg-white">
              <div className="flex justify-between items-start">
                <h2 className="text-lg font-semibold text-gray-900">{insight.theme}</h2>
                <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full whitespace-nowrap ml-2">
                  {insight.frequency}× frequency
                </span>
              </div>

              <div>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Core Problem</h3>
                <p className="text-gray-900 text-sm">{insight.problem}</p>
              </div>

              {insight.root_cause && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Root Cause</h3>
                  <p className="text-gray-900 text-sm">{insight.root_cause}</p>
                </div>
              )}

              {Array.isArray(insight.evidence) && insight.evidence.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Evidence</h3>
                  <ul className="list-disc pl-4 space-y-1 text-sm bg-gray-50 p-3 rounded-lg text-gray-700 italic">
                    {(insight.evidence as string[]).map((q, i) => (
                      <li key={i}>&ldquo;{q}&rdquo;</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}

          {insights.length === 0 && !isLoading && (
            <div className="col-span-full text-center py-16 text-gray-400 border-2 border-dashed rounded-xl">
              <p className="text-lg mb-2">No insights yet</p>
              <p className="text-sm">Add signals first, then click &ldquo;Generate Insights&rdquo;.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
