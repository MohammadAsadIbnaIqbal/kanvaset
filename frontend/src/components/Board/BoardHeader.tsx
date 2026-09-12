import React, { useState } from "react";
import { ArrowLeft, Check, Download, Share2 } from "lucide-react";
import type { ConnectionStatus } from "../../hooks/useWebSocketBoard";
import type { PresenceUser } from "../../types/board";

interface BoardHeaderProps {
  title: string;
  revision: number;
  connectionStatus: ConnectionStatus;
  presence: PresenceUser[];
  role: "OWNER" | "EDITOR" | "VIEWER";
  onBack: () => void;
  onOpenShare: () => void;
  onExport: (format: "json" | "png") => void;
  onRename?: (newName: string) => void;
}

export const BoardHeader: React.FC<BoardHeaderProps> = ({
  title,
  revision,
  connectionStatus,
  presence,
  role,
  onBack,
  onOpenShare,
  onExport,
  onRename,
}) => {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitleVal, setEditTitleVal] = useState(title);

  const handleTitleSubmit = () => {
    setIsEditingTitle(false);
    if (editTitleVal.trim() && editTitleVal !== title && onRename) {
      onRename(editTitleVal.trim());
    }
  };

  const statusColors = {
    connected: "bg-emerald-500 text-emerald-400 border-emerald-500/30",
    reconnecting: "bg-amber-500 text-amber-400 border-amber-500/30 animate-pulse",
    connecting: "bg-sky-500 text-sky-400 border-sky-500/30 animate-pulse",
    disconnected: "bg-rose-500 text-rose-400 border-rose-500/30",
  };

  return (
    <div className="h-14 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 px-4 flex items-center justify-between z-30 select-none">
      <div className="flex items-center space-x-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          title="Back to Dashboard"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        {isEditingTitle && role !== "VIEWER" ? (
          <div className="flex items-center space-x-1">
            <input
              type="text"
              autoFocus
              value={editTitleVal}
              onChange={(e) => setEditTitleVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleTitleSubmit();
                if (e.key === "Escape") setIsEditingTitle(false);
              }}
              onBlur={handleTitleSubmit}
              className="bg-slate-800 border border-indigo-500 rounded-lg px-2.5 py-1 text-sm text-white font-semibold focus:outline-none"
            />
            <button
              onClick={handleTitleSubmit}
              className="p-1 text-emerald-400 hover:bg-slate-800 rounded"
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center space-x-2">
            <h1
              onClick={() => {
                if (role !== "VIEWER") setIsEditingTitle(true);
              }}
              className={`text-sm sm:text-base font-semibold text-white tracking-tight ${
                role !== "VIEWER" ? "hover:text-indigo-400 cursor-pointer" : ""
              }`}
            >
              {title}
            </h1>
            <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              {role}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* Connection status badge */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border bg-opacity-10 ${
            statusColors[connectionStatus]
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              connectionStatus === "connected" ? "bg-emerald-400" : "bg-amber-400"
            }`}
          />
          <span className="capitalize hidden sm:inline">{connectionStatus}</span>
          <span className="text-[10px] text-slate-400 pl-1 border-l border-slate-700">
            r{revision}
          </span>
        </div>

        {/* Presence Avatars */}
        <div className="flex items-center -space-x-2">
          {presence.slice(0, 5).map((u) => (
            <div
              key={u.user_id}
              title={`${u.username} (${u.role})`}
              style={{ backgroundColor: u.color }}
              className="w-7 h-7 rounded-full border-2 border-slate-900 flex items-center justify-center text-white text-[11px] font-bold shadow-md shadow-black/40 uppercase cursor-default"
            >
              {u.username.charAt(0)}
            </div>
          ))}
          {presence.length > 5 && (
            <div className="w-7 h-7 rounded-full bg-slate-800 border-2 border-slate-900 flex items-center justify-center text-slate-300 text-[10px] font-bold">
              +{presence.length - 5}
            </div>
          )}
        </div>

        {/* Share Button (Owner/Editor) */}
        {role === "OWNER" && (
          <button
            onClick={onOpenShare}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 cursor-pointer transition-colors"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Share</span>
          </button>
        )}

        {/* Export Dropdown */}
        <div className="relative group">
          <button
            onClick={() => onExport("json")}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            title="Export Board"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
