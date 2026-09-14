import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Share2 } from "lucide-react";
import { api } from "../../services/api";
import { useWebSocketProject } from "../../hooks/useWebSocketProject";
import { useAuth } from "../../context/AuthContext";
import { TaskCard } from "./TaskCard";
import { TaskDetailModal } from "./TaskDetailModal";
import { ActivitySidebar } from "./ActivitySidebar";
import { TaskHistoryModal } from "./TaskHistoryModal";
import { ProjectShareModal } from "./ProjectShareModal";
import type { Project, Task } from "../../types/project";

export const ProjectPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  
  const {
    tasks,
    activities,
    createTask,
    updateTask,
    connectionStatus,
  } = useWebSocketProject({
    projectId: projectId!,
    token: localStorage.getItem("kanvaset_token"),
    currentUser: user,
  });

  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [historyTask, setHistoryTask] = useState<Task | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);

  useEffect(() => {
    async function loadProject() {
      try {
        if (!projectId) return;
        setLoading(true);
        const data = await api.getProject(projectId);
        setProject(data);
      } catch (err) {
        console.error("Failed to load project details", err);
      } finally {
        setLoading(false);
      }
    }
    loadProject();
  }, [projectId]);

  const handleCreateTask = (status: string) => {
    const id = `task_${Date.now()}`;
    createTask({
      id,
      title: "New Task",
      status,
      priority: "MEDIUM",
    });
  };

  const activeTasks = tasks.filter((t) => !t.is_deleted);

  const columns = [
    { id: "TODO", title: "To Do" },
    { id: "IN_PROGRESS", title: "In Progress" },
    { id: "DONE", title: "Done" },
  ];

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-950 text-slate-400 h-screen">
        <span className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
        <p className="text-sm">Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-950 text-rose-400 h-screen">
        Project not found.
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 overflow-hidden text-slate-200">
      <header className="h-14 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate("/")}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">
              {project.name}
            </h1>
            <div className="flex items-center space-x-2 text-[10px] text-slate-400">
              <span className="flex items-center space-x-1">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    connectionStatus === "connected"
                      ? "bg-emerald-500"
                      : connectionStatus === "connecting" || connectionStatus === "reconnecting"
                      ? "bg-amber-500"
                      : "bg-rose-500"
                  }`}
                />
                <span className="capitalize">{connectionStatus}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Share Button (Only for OWNER/EDITOR usually, but we'll show it if project is loaded) */}
        {project && (
          <button
            onClick={() => setShowShareModal(true)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-colors cursor-pointer text-xs font-semibold"
          >
            <Share2 className="w-4 h-4" />
            <span>Share</span>
          </button>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 flex overflow-x-auto p-6 gap-6 items-start">
          {columns.map((col) => (
            <div
              key={col.id}
              className="w-80 flex-shrink-0 flex flex-col bg-slate-900/50 rounded-2xl border border-slate-800/80 max-h-full"
            >
              <div className="p-4 flex items-center justify-between border-b border-slate-800/80">
                <h3 className="text-sm font-bold text-white">{col.title}</h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                  {activeTasks.filter((t) => t.status === col.id).length}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {activeTasks
                  .filter((t) => t.status === col.id)
                  .map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={(t) => setSelectedTask(t)}
                    />
                  ))}
                <button
                  onClick={() => handleCreateTask(col.id)}
                  className="w-full flex items-center justify-center space-x-2 p-3 rounded-xl border-2 border-dashed border-slate-800 text-slate-500 hover:text-indigo-400 hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span className="text-xs font-semibold">Add Task</span>
                </button>
              </div>
            </div>
          ))}
        </main>
        
        <ActivitySidebar activities={activities} />
      </div>

      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          updateTask={updateTask}
          onViewHistory={(t) => setHistoryTask(t)}
        />
      )}

      {historyTask && (
        <TaskHistoryModal
          task={historyTask}
          onClose={() => setHistoryTask(null)}
          onRestore={(updates) => {
            updateTask(historyTask.id, updates);
            setSelectedTask({ ...historyTask, ...updates, version: historyTask.version + 1 });
          }}
        />
      )}

      {showShareModal && (
        <ProjectShareModal
          projectId={project.id}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
};
