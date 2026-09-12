import React, { useState, useRef, useEffect } from "react";
import { ArrowLeft, Check, Download, Share2, ChevronDown, FileJson, Image as ImageIcon } from "lucide-react";
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
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setShowExportMenu(false);
      }
    };
    if (showExportMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showExportMenu]);

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
        <div className="relative" ref={exportMenuRef}>
          <button
            onClick={() => setShowExportMenu((prev) => !prev)}
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-750 border border-slate-700 text-xs font-semibold transition-colors cursor-pointer"
            title="Export Board Options"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export</span>
            <ChevronDown className="w-3 h-3 text-slate-400 ml-0.5" />
          </button>

          {showExportMenu && (
            <div className="absolute right-0 mt-2 w-48 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
              <button
                onClick={() => {
                  onExport("png");
                  setShowExportMenu(false);
                }}
                className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs text-left text-slate-200 hover:bg-indigo-600/20 hover:text-indigo-300 transition-colors cursor-pointer"
              >
                <ImageIcon className="w-4 h-4 text-indigo-400 shrink-0" />
                <div>
                  <div className="font-semibold">Export as PNG</div>
                  <div className="text-[10px] text-slate-400">High-resolution canvas image</div>
                </div>
              </button>
              <div className="h-px bg-slate-800 my-1" />
              <button
                onClick={() => {
                  onExport("json");
                  setShowExportMenu(false);
                }}
                className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs text-left text-slate-200 hover:bg-indigo-600/20 hover:text-indigo-300 transition-colors cursor-pointer"
              >
                <FileJson className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-semibold">Export as JSON</div>
                  <div className="text-[10px] text-slate-400">Full board state & objects</div>
                </div>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
