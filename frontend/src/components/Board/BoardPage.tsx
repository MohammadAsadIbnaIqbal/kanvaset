import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWebSocketBoard } from "../../hooks/useWebSocketBoard";
import { api } from "../../services/api";
import type { Board } from "../../types/board";
import { BoardCanvas } from "./Canvas/BoardCanvas";
import { BoardHeader } from "./BoardHeader";
import { ShareModal } from "./ShareModal";
import type { ToolType } from "./Toolbar";
import { Toolbar } from "./Toolbar";

interface BoardPageProps {
  boardId: string;
  onBack: () => void;
}

export const BoardPage: React.FC<BoardPageProps> = ({ boardId, onBack }) => {
  const { user, token } = useAuth();
  const [boardInfo, setBoardInfo] = useState<Board | null>(null);
  const [loading, setLoading] = useState(true);

  // Active tool and styling state
  const [activeTool, setActiveTool] = useState<ToolType>("select");
  const [selectedColor, setSelectedColor] = useState<string>("#FEF08A");
  const [zoom, setZoom] = useState<number>(1.0);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);

  // Real-time WebSocket hook
  const {
    objects,
    presence,
    cursors,
    role,
    serverRevision,
    connectionStatus,
    sendCursor,
    createObject,
    moveObject,
    resizeObject,
    updateObject,
    deleteObject,
  } = useWebSocketBoard({
    boardId,
    token,
    currentUser: user,
  });

  useEffect(() => {
    async function loadBoard() {
      try {
        setLoading(true);
        const b = await api.getBoard(boardId);
        setBoardInfo(b);
      } catch (err) {
        console.error("Failed to load board details:", err);
      } finally {
        setLoading(false);
      }
    }
    loadBoard();
  }, [boardId]);

  const handleRename = async (newName: string) => {
    try {
      const updated = await api.updateBoard(boardId, { name: newName });
      setBoardInfo(updated);
    } catch (err) {
      console.error("Failed to rename board:", err);
    }
  };

  const handleExport = (format: "json" | "png") => {
    if (format === "json") {
      const dataStr = JSON.stringify(
        {
          board: boardInfo,
          objects,
          exported_at: new Date().toISOString(),
        },
        null,
        2
      );
      const blob = new Blob([dataStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${boardInfo?.name || "board"}_export.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (loading && !boardInfo) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-950 text-slate-400">
        <span className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-screen w-screen overflow-hidden bg-slate-950 select-none relative">
      {/* Board Top Navigation */}
      <BoardHeader
        title={boardInfo?.name || "Untitled Board"}
        revision={serverRevision}
        connectionStatus={connectionStatus}
        presence={presence}
        role={role}
        onBack={onBack}
        onOpenShare={() => setShowShareModal(true)}
        onExport={handleExport}
        onRename={handleRename}
      />

      {/* Main Canvas Area */}
      <div className="flex-1 relative overflow-hidden">
        <BoardCanvas
          objects={objects}
          cursors={cursors}
          role={role}
          activeTool={activeTool}
          selectedColor={selectedColor}
          zoom={zoom}
          onZoomChange={setZoom}
          onSendCursor={sendCursor}
          onCreateObject={createObject}
          onMoveObject={moveObject}
          onResizeObject={resizeObject}
          onUpdateObject={updateObject}
          onDeleteObject={deleteObject}
          onSelectObject={setSelectedObjectId}
          selectedObjectId={selectedObjectId}
        />

        {/* Floating Action Toolbar */}
        <Toolbar
          activeTool={activeTool}
          onSelectTool={setActiveTool}
          selectedColor={selectedColor}
          onSelectColor={setSelectedColor}
          hasSelection={selectedObjectId !== null}
          onDeleteSelection={() => {
            if (selectedObjectId) {
              deleteObject(selectedObjectId);
              setSelectedObjectId(null);
            }
          }}
          zoom={zoom}
          onZoomIn={() => setZoom((z) => Math.min(z * 1.15, 3.0))}
          onZoomOut={() => setZoom((z) => Math.max(z * 0.85, 0.2))}
          onResetZoom={() => setZoom(1.0)}
          isViewer={role === "VIEWER"}
        />
      </div>

      {/* Share Modal Dialog */}
      {showShareModal && (
        <ShareModal
          boardId={boardId}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
};
