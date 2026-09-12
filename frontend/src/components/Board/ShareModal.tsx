import React, { useEffect, useState } from "react";
import { Shield, UserPlus, X } from "lucide-react";
import { api } from "../../services/api";
import type { BoardMember } from "../../types/board";

interface ShareModalProps {
  boardId: string;
  onClose: () => void;
}

export const ShareModal: React.FC<ShareModalProps> = ({ boardId, onClose }) => {
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [userQuery, setUserQuery] = useState("");
  const [role, setRole] = useState<"OWNER" | "EDITOR" | "VIEWER">("EDITOR");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMembers = async () => {
    try {
      const data = await api.getBoardMembers(boardId);
      setMembers(data);
    } catch (err) {
      console.error("Failed to load members:", err);
    }
  };

  useEffect(() => {
    loadMembers();
  }, [boardId]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userQuery.trim()) return;
    setError(null);
    setLoading(true);

    try {
      await api.addBoardMember(boardId, userQuery.trim(), role);
      setUserQuery("");
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to add member");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-bold text-white">Share Board & Permissions</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {error}
          </div>
        )}

        {/* Invite form */}
        <form onSubmit={handleAddMember} className="mt-4 space-y-3">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Invite by Email or Username
          </label>
          <div className="flex space-x-2">
            <input
              type="text"
              required
              value={userQuery}
              onChange={(e) => setUserQuery(e.target.value)}
              placeholder="user@example.com or username"
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as any)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-2 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="EDITOR">Editor</option>
              <option value="VIEWER">Viewer</option>
              <option value="OWNER">Owner</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>{loading ? "Adding..." : "Grant Access"}</span>
          </button>
        </form>

        {/* Current members list */}
        <div className="mt-6 pt-4 border-t border-slate-800">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Board Members ({members.length})
          </h4>
          <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
            {members.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between p-2 rounded-xl bg-slate-800/60 border border-slate-700/50 text-xs"
              >
                <div className="flex items-center space-x-2.5 truncate">
                  <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-[10px] uppercase">
                    {m.username.charAt(0)}
                  </div>
                  <div className="truncate">
                    <div className="font-medium text-white truncate">{m.username}</div>
                    <div className="text-[10px] text-slate-400 truncate">{m.email}</div>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    m.role === "OWNER"
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                      : m.role === "EDITOR"
                      ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/30"
                      : "bg-slate-700/50 text-slate-300 border-slate-600"
                  }`}
                >
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
