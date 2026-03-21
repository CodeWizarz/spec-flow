import React, { useEffect } from "react";
import { useParams } from "react-router";
import { SpecStore } from "@plane/shared-state";
import { Button } from "@plane/ui";

const specStore = new SpecStore();

export default function WorkspaceSpecsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  useEffect(() => {
    if (workspaceSlug) {
      specStore.fetchSpecs(workspaceSlug);
    }
  }, [workspaceSlug]);

  const handleGenerate = async () => {
    if (!workspaceSlug) return;
    await specStore.generateSpec(workspaceSlug);
    alert("Spec generation queued based on Top 20 recent insights. Refresh soon.");
  };

  const downloadMarkdown = (spec: any) => {
    const json = spec.spec_json || {};
    let md = `# ${json.feature_name || spec.title}\\n\\n`;
    md += `## Problem\\n${json.problem || ""}\\n\\n`;
    md += `## User Story\\n${json.user_story || ""}\\n\\n`;
    md += `## Proposed Solution\\n${json.solution || ""}\\n\\n`;

    if (json.ui_changes?.length) {
      md += `## UI Changes\\n`;
      json.ui_changes.forEach((c: string) => md += `- ${c}\\n`);
      md += `\\n`;
    }

    if (json.data_model_changes?.length) {
      md += `## Data Model Changes\\n`;
      json.data_model_changes.forEach((c: string) => md += `- ${c}\\n`);
      md += `\\n`;
    }

    if (json.workflow_changes?.length) {
      md += `## Workflow Changes\\n`;
      json.workflow_changes.forEach((c: string) => md += `- ${c}\\n`);
      md += `\\n`;
    }

    if (json.tasks?.length) {
      md += `## Agent Development Tasks\\n\\n`;
      json.tasks.forEach((task: any, index: number) => {
        md += `### Task ${index + 1}\\n`;
        md += `<read_first>\\n`;
        (task.read_first || []).forEach((f: string) => md += `- ${f}\\n`);
        md += `</read_first>\\n`;
        md += `<action>\\n`;
        (task.action || []).forEach((a: string) => md += `- ${a}\\n`);
        md += `</action>\\n\\n`;
      });
    }

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${spec.title.replace(/\\s+/g, "_")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Generated AI Specs</h1>
          <p className="text-gray-500">Structured execution plans ready for autonomous coding agents.</p>
        </div>
        <Button onClick={handleGenerate} disabled={specStore.isGenerating}>
          {specStore.isGenerating ? "Generating..." : "Generate from Insights"}
        </Button>
      </div>

      {specStore.error && <p className="text-red-500">{specStore.error}</p>}

      {specStore.isLoading ? (
        <p>Loading specs...</p>
      ) : (
        <div className="space-y-8">
          {specStore.specs.map((spec) => {
            const json = spec.spec_json || {};
            return (
              <div key={spec.id} className="border p-6 rounded-xl shadow-sm bg-white">
                <div className="flex justify-between items-start mb-4 border-b pb-4">
                  <div>
                    <h2 className="text-xl font-bold">{json.feature_name || spec.title}</h2>
                    <p className="text-sm text-gray-500 mt-1">Generated: {new Date(spec.created_at).toLocaleString()}</p>
                  </div>
                  <Button onClick={() => downloadMarkdown(spec)} variant="outline">
                    Download .md
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-semibold text-gray-700">Problem</h3>
                    <p className="text-sm mt-1">{json.problem}</p>
                    <h3 className="font-semibold text-gray-700 mt-4">User Story</h3>
                    <p className="text-sm italic mt-1">{json.user_story}</p>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-700">Solution</h3>
                    <p className="text-sm mt-1">{json.solution}</p>
                  </div>
                </div>

                <div className="mt-6">
                  <h3 className="font-semibold text-gray-700 mb-2">Architecture Changes</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div className="bg-gray-50 p-3 rounded">
                      <span className="font-medium text-blue-800 block mb-1">UI</span>
                      <ul className="list-disc pl-4 space-y-1">
                        {(json.ui_changes || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                      </ul>
                    </div>
                    <div className="bg-gray-50 p-3 rounded">
                      <span className="font-medium text-green-800 block mb-1">Data Model</span>
                      <ul className="list-disc pl-4 space-y-1">
                        {(json.data_model_changes || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                      </ul>
                    </div>
                    <div className="bg-gray-50 p-3 rounded">
                      <span className="font-medium text-purple-800 block mb-1">Workflow</span>
                      <ul className="list-disc pl-4 space-y-1">
                        {(json.workflow_changes || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="mt-6 border-t pt-4">
                  <h3 className="font-semibold text-gray-700 mb-2">Agent Tasks ({json.tasks?.length || 0})</h3>
                  <div className="space-y-3">
                    {(json.tasks || []).map((task: any, index: number) => (
                      <div key={index} className="bg-gray-100 p-3 rounded text-sm font-mono">
                        <div className="text-gray-500 mb-1">&lt;read_first&gt;</div>
                        <ul className="pl-4 text-orange-700 list-disc">
                          {(task.read_first || []).map((f: string, i: number) => <li key={i}>{f}</li>)}
                        </ul>
                        <div className="text-gray-500 mb-1 mt-2">&lt;action&gt;</div>
                        <ul className="pl-4 text-blue-700 list-disc">
                          {(task.action || []).map((a: string, i: number) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
          {specStore.specs.length === 0 && (
            <div className="text-center py-12 text-gray-500 border rounded-xl">
              No specs generated yet. Click Generate to convert insights into specifications.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
