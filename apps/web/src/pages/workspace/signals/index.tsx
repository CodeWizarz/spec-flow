import React, { useEffect, useState } from "react";
import { useParams } from "react-router";
import { SignalStore } from "@plane/shared-state";
// Assuming @plane/ui components
import { Button, Input, Table } from "@plane/ui";

// Initialize store (usually from MobX contextProvider)
const signalStore = new SignalStore();

export default function WorkspaceSignalsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const [isModalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (workspaceSlug) {
      signalStore.fetchSignals(workspaceSlug);
    }
  }, [workspaceSlug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceSlug) return;

    const formData = new FormData();
    formData.append("title", title);
    if (file) {
      formData.append("file", file);
    }

    await signalStore.createSignal(workspaceSlug, formData);
    setModalOpen(false);
    setTitle("");
    setFile(null);
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Customer Signals</h1>
        <Button onClick={() => setModalOpen(true)}>Upload Feedback</Button>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">New Signal</h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input 
                placeholder="Signal Title" 
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
              <input 
                type="file" 
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <div className="flex justify-end gap-2 mt-4">
                <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={signalStore.isLoading}>Submit</Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {signalStore.isLoading && signalStore.signals.length === 0 ? (
        <p>Loading signals...</p>
      ) : (
        <div className="border rounded-md">
          <table className="w-full text-left">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="p-3">Title</th>
                <th className="p-3">Status</th>
                <th className="p-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {signalStore.signals.map((sig) => (
                <tr key={sig.id} className="border-b hover:bg-gray-50">
                  <td className="p-3">{sig.title}</td>
                  <td className="p-3">{sig.processing_status}</td>
                  <td className="p-3">{sig.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
