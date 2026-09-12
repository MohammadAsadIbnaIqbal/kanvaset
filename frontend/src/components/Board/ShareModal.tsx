import React, { useEffect, useState } from "react";
import { CheckCircle2, Shield, Trash2, UserPlus, X } from "lucide-react";
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
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

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
    setSuccessMsg(null);
    setLoading(true);

    try {
      await api.addBoardMember(boardId, userQuery.trim(), role);
      setSuccessMsg(`Successfully shared board with ${userQuery.trim()}!`);
      setUserQuery("");
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to add member");
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    setError(null);
    setSuccessMsg(null);
    try {
      await api.updateBoardMember(boardId, userId, newRole);
      setSuccessMsg("Member role updated successfully.");
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to update member role");
    }
  };

  const handleRemoveMember = async (userId: string, username: string) => {
    if (!confirm(`Are you sure you want to remove ${username}'s access to this board?`)) return;
    setError(null);
    setSuccessMsg(null);
    try {
      await api.removeBoardMember(boardId, userId);
      setSuccessMsg(`Access revoked for ${username}.`);
      await loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to remove member");
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
            aria-label="Close share modal"
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mt-4 p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
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
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-md shadow-indigo-600/30"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>{loading ? "Inviting..." : "Grant Access"}</span>
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
                className="flex items-center justify-between p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/50 text-xs"
              >
                <div className="flex items-center space-x-2.5 truncate max-w-[190px]">
                  <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-[10px] uppercase shrink-0">
                    {m.username.charAt(0)}
                  </div>
                  <div className="truncate">
                    <div className="font-medium text-white truncate">{m.username}</div>
                    <div className="text-[10px] text-slate-400 truncate">{m.email}</div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  {m.role === "OWNER" ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-amber-500/10 text-amber-400 border-amber-500/30">
                      OWNER
                    </span>
                  ) : (
                    <>
                      <select
                        value={m.role}
                        onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                        className="bg-slate-800 border border-slate-700 text-slate-200 text-[10px] font-semibold rounded-lg px-2 py-0.5 outline-none cursor-pointer hover:border-slate-600"
                      >
                        <option value="EDITOR">EDITOR</option>
                        <option value="VIEWER">VIEWER</option>
                      </select>
                      <button
                        onClick={() => handleRemoveMember(m.user_id, m.username)}
                        title="Revoke access"
                        className="p-1 rounded-md text-slate-400 hover:text-rose-400 hover:bg-slate-700/60 transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
