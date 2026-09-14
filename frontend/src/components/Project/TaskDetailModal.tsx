import React, { useState, useEffect } from "react";
import { X, Clock } from "lucide-react";
import type { Task } from "../../types/project";

interface TaskDetailModalProps {
  task: Task;
  onClose: () => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  onViewHistory: (task: Task) => void;
}

export const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  task,
  onClose,
  updateTask,
  onViewHistory,
}) => {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description || "");
  const [status, setStatus] = useState(task.status);
  const [priority, setPriority] = useState(task.priority);

  // Sync state if task changes externally
  useEffect(() => {
    setTitle(task.title);
    setDescription(task.description || "");
    setStatus(task.status);
    setPriority(task.priority);
  }, [task]);

  const handleTitleBlur = () => {
    if (title !== task.title) {
      updateTask(task.id, { title });
    }
  };

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (title !== task.title) {
        updateTask(task.id, { title });
      }
    }
  };

  // Debounced description update
  useEffect(() => {
    const handler = setTimeout(() => {
      if (description !== (task.description || "")) {
        updateTask(task.id, { description });
      }
    }, 1000);
    return () => clearTimeout(handler);
  }, [description, task.description, task.id, updateTask]);

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value;
    setStatus(newStatus);
    updateTask(task.id, { status: newStatus });
  };

  const handlePriorityChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPriority = e.target.value;
    setPriority(newPriority);
    updateTask(task.id, { priority: newPriority });
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-medium text-slate-400">Task Details</span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onViewHistory(task)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-xs font-semibold"
            >
              <Clock className="w-4 h-4" />
              <span>History</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={handleTitleBlur}
              onKeyDown={handleTitleKeyDown}
              className="w-full bg-transparent text-2xl font-bold text-white border-none focus:outline-none focus:ring-0 placeholder:text-slate-600"
              placeholder="Task Title"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">Status</label>
              <select
                value={status}
                onChange={handleStatusChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="TODO">To Do</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="DONE">Done</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">Priority</label>
              <select
                value={priority}
                onChange={handlePriorityChange}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 resize-none min-h-[150px]"
              placeholder="Add a more detailed description..."
            />
          </div>
        </div>
      </div>
    </div>
  );
};
