import React, { useEffect, useState } from "react";
import { FolderPlus, Layout, Plus, Trash2 } from "lucide-react";
import { api } from "../../services/api";
import type { Board, Workspace } from "../../types/board";

interface DashboardPageProps {
  onSelectBoard: (boardId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onSelectBoard }) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWs, setSelectedWs] = useState<Workspace | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [showNewWsModal, setShowNewWsModal] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [showNewBoardModal, setShowNewBoardModal] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [newBoardDesc, setNewBoardDesc] = useState("");

  const loadWorkspaces = async () => {
    try {
      setLoading(true);
      let list = await api.getWorkspaces();
      if (list.length === 0) {
        // Automatically create a default workspace for new user
        const def = await api.createWorkspace("My Personal Workspace");
        list = [def];
      }
      setWorkspaces(list);
      if (!selectedWs && list.length > 0) {
        setSelectedWs(list[0]);
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspaces();
  }, []);

  useEffect(() => {
    async function loadBoards() {
      if (!selectedWs) return;
      try {
        const bList = await api.getWorkspaceBoards(selectedWs.id);
        setBoards(bList);
      } catch (err) {
        console.error("Failed to load boards:", err);
      }
    }
    loadBoards();
  }, [selectedWs]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    try {
      const ws = await api.createWorkspace(newWsName.trim());
      setWorkspaces((prev) => [ws, ...prev]);
      setSelectedWs(ws);
      setNewWsName("");
      setShowNewWsModal(false);
    } catch {
      alert("Failed to create workspace");
    }
  };

  const handleCreateBoard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWs || !newBoardName.trim()) return;
    try {
      const b = await api.createBoard(selectedWs.id, newBoardName.trim(), newBoardDesc.trim());
      setBoards((prev) => [b, ...prev]);
      setNewBoardName("");
      setNewBoardDesc("");
      setShowNewBoardModal(false);
    } catch {
      alert("Failed to create board");
    }
  };

  const handleDeleteBoard = async (boardId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this board?")) return;
    try {
      await api.deleteBoard(boardId);
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } catch {
      alert("Failed to delete board");
    }
  };

  if (loading && workspaces.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-950 text-slate-400">
        <span className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex bg-slate-950 overflow-hidden">
      {/* Workspace Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Workspaces
          </h2>
          <button
            onClick={() => setShowNewWsModal(true)}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            title="Create Workspace"
          >
            <FolderPlus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {workspaces.map((ws) => (
            <button
              key={ws.id}
              onClick={() => setSelectedWs(ws)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium flex items-center justify-between transition-colors cursor-pointer ${
                selectedWs?.id === ws.id
                  ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/30"
                  : "text-slate-300 hover:bg-slate-800/60"
              }`}
            >
              <div className="flex items-center space-x-2.5 truncate">
                <Layout className="w-4 h-4 shrink-0 text-slate-400" />
                <span className="truncate">{ws.name}</span>
              </div>
              <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                {ws.role}
              </span>
            </button>
          ))}
        </div>
      </aside>

      {/* Main Boards View */}
      <main className="flex-1 flex flex-col overflow-y-auto p-8">
        {selectedWs ? (
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-800 gap-4">
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  {selectedWs.name}
                </h1>
                <p className="text-sm text-slate-400 mt-1">
                  Manage whiteboards and real-time collaborative workspaces.
                </p>
              </div>

              <button
                onClick={() => setShowNewBoardModal(true)}
                className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/20 cursor-pointer transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>New Board</span>
              </button>
            </div>

            {/* Board Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
              {boards.map((b) => (
                <div
                  key={b.id}
                  onClick={() => onSelectBoard(b.id)}
                  className="group bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-5 shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between hover:-translate-y-0.5"
                >
                  <div>
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-xl bg-indigo-600/15 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                        <Layout className="w-5 h-5" />
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                          {b.role}
                        </span>
                        {b.role === "OWNER" && (
                          <button
                            onClick={(e) => handleDeleteBoard(b.id, e)}
                            title="Delete Board"
                            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    <h3 className="text-base font-semibold text-white mt-4 group-hover:text-indigo-400 transition-colors">
                      {b.name}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1 min-h-[32px]">
                      {b.description || "No description provided."}
                    </p>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                    <span>Revision: {b.revision}</span>
                    <span>{b.objects_count ?? 0} objects</span>
                  </div>
                </div>
              ))}

              {boards.length === 0 && (
                <div className="col-span-full py-16 text-center border-2 border-dashed border-slate-800 rounded-2xl">
                  <Layout className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <h3 className="text-base font-semibold text-slate-300">No boards yet</h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Create your first board to start drawing, brainstorming, and collaborating in real time.
                  </p>
                  <button
                    onClick={() => setShowNewBoardModal(true)}
                    className="mt-4 inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 text-xs font-semibold cursor-pointer transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Create Board</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            Select or create a workspace to view boards.
          </div>
        )}
      </main>

      {/* New Workspace Modal */}
      {showNewWsModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Create New Workspace</h3>
            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  Workspace Name
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={newWsName}
                  onChange={(e) => setNewWsName(e.target.value)}
                  placeholder="e.g. Design Team"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewWsModal(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Board Modal */}
      {showNewBoardModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Create New Board</h3>
            <form onSubmit={handleCreateBoard} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  Board Name
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={newBoardName}
                  onChange={(e) => setNewBoardName(e.target.value)}
                  placeholder="e.g. Sprint 42 Retrospective"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  Description (Optional)
                </label>
                <textarea
                  value={newBoardDesc}
                  onChange={(e) => setNewBoardDesc(e.target.value)}
                  placeholder="What is this board for?"
                  rows={2}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewBoardModal(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                >
                  Create Board
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
