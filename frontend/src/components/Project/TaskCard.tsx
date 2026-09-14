import React from "react";
import type { Task } from "../../types/project";

interface TaskCardProps {
  task: Task;
  onClick: (task: Task) => void;
}

const priorityColors: Record<string, string> = {
  LOW: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  MEDIUM: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  HIGH: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  URGENT: "bg-rose-500/10 text-rose-400 border-rose-500/20",
};

export const TaskCard: React.FC<TaskCardProps> = ({ task, onClick }) => {
  return (
    <div
      onClick={() => onClick(task)}
      className="bg-slate-800 border border-slate-700 hover:border-indigo-500/50 rounded-xl p-4 shadow-sm cursor-pointer transition-all hover:-translate-y-0.5 active:translate-y-0 group"
    >
      <div className="flex justify-between items-start mb-2">
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
            priorityColors[task.priority] || priorityColors.MEDIUM
          }`}
        >
          {task.priority}
        </span>
      </div>
      
      <h4 className="text-sm font-semibold text-white mb-2 line-clamp-2 group-hover:text-indigo-400 transition-colors">
        {task.title}
      </h4>
      
      {task.tags && task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {task.tags.map((tag: string, idx: number) => (
            <span
              key={idx}
              className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-300 border border-slate-600/50"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
