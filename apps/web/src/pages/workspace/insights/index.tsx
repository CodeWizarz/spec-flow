import React, { useEffect } from "react";
import { useParams } from "react-router";
import { InsightStore } from "@plane/shared-state";
import { Button } from "@plane/ui";

const insightStore = new InsightStore();

export default function WorkspaceInsightsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  useEffect(() => {
    if (workspaceSlug) {
      insightStore.fetchInsights(workspaceSlug);
    }
  }, [workspaceSlug]);

  const handleGenerate = async () => {
    if (!workspaceSlug) return;
    await insightStore.generateInsights(workspaceSlug);
    alert("Generation queued! Refresh in a few moments.");
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">AI Insights</h1>
          <p className="text-gray-500">Discover recurring themes and root causes extracted from raw signals.</p>
        </div>
        <Button onClick={handleGenerate} disabled={insightStore.isGenerating}>
          {insightStore.isGenerating ? "Generating..." : "Generate Insights"}
        </Button>
      </div>

      {insightStore.error && <p className="text-red-500">{insightStore.error}</p>}

      {insightStore.isLoading ? (
        <p>Loading insights...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {insightStore.insights.map((insight) => (
            <div key={insight.id} className="border p-4 rounded-lg shadow-sm flex flex-col gap-3">
              <div className="flex justify-between items-start">
                <h2 className="text-lg font-semibold">{insight.theme}</h2>
                <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">{insight.frequency} occurrences</span>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500">Core Problem</h3>
                <p className="text-gray-900 mt-1">{insight.problem}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-gray-500">Root Cause</h3>
                <p className="text-gray-900 mt-1">{insight.root_cause}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Evidence</h3>
                <ul className="list-disc pl-5 space-y-1 text-sm bg-gray-50 p-3 rounded text-gray-700 italic">
                  {Array.isArray(insight.evidence) && insight.evidence.map((quote: string, i: number) => (
                    <li key={i}>"{quote}"</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
          {insightStore.insights.length === 0 && (
            <div className="col-span-full text-center py-12 text-gray-500">
              No insights generated yet. Click Generate Insights to process active signals.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
