import React, { useEffect, useState } from "react";
import { X, RotateCcw } from "lucide-react";
import { api } from "../../services/api";
import type { Task } from "../../types/project";

interface TaskHistoryModalProps {
  task: Task;
  onClose: () => void;
  onRestore: (updates: Partial<Task>) => void;
}

export const TaskHistoryModal: React.FC<TaskHistoryModalProps> = ({
  task,
  onClose,
  onRestore,
}) => {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHistory() {
      try {
        setLoading(true);
        const data = await api.getTaskHistory(task.project_id, task.id);
        setHistory(data);
      } catch (err) {
        setError("Failed to load task history.");
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [task.id, task.project_id]);

  const handleRestore = (version: any) => {
    if (confirm("Are you sure you want to restore to this version?")) {
      onRestore({
        title: version.title,
        description: version.description,
        status: version.status,
        priority: version.priority,
      });
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <h3 className="text-sm font-semibold text-white">Task History: {task.title}</h3>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading ? (
            <div className="text-center py-8 text-slate-400 text-sm flex flex-col items-center justify-center space-y-2">
              <span className="w-6 h-6 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <span>Loading history...</span>
            </div>
          ) : error ? (
            <div className="text-center py-8 text-rose-400 text-sm">{error}</div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">No history available.</div>
          ) : (
            <div className="relative pl-4 space-y-6">
              <div className="absolute left-2.5 top-2 bottom-2 w-px bg-slate-800"></div>
              {history.map((ver, idx) => (
                <div key={idx} className="relative pl-6">
                  <div className="absolute left-0 top-1.5 w-2 h-2 rounded-full bg-slate-600 border border-slate-500 -ml-1"></div>
                  <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-semibold text-slate-300">
                        Version {ver.version}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(ver.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-sm text-white mb-1 font-medium">{ver.title}</div>
                    <div className="text-xs text-slate-400 mb-3 flex space-x-2">
                      <span>Status: {ver.status}</span>
                      <span>•</span>
                      <span>Priority: {ver.priority}</span>
                    </div>
                    
                    <button
                      onClick={() => handleRestore(ver)}
                      className="inline-flex items-center space-x-1.5 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-1 rounded transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Restore this version</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
