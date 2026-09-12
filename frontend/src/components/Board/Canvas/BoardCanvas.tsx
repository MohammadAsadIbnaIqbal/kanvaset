import React, { useCallback, useEffect, useRef, useState } from "react";
import type { BoardObject } from "../../../types/board";
import type { ToolType } from "../Toolbar";

interface BoardCanvasProps {
  objects: BoardObject[];
  cursors: Record<string, { x: number; y: number; username: string; color: string }>;
  role: "OWNER" | "EDITOR" | "VIEWER";
  activeTool: ToolType;
  selectedColor: string;
  zoom: number;
  onZoomChange: (z: number) => void;
  onSendCursor: (x: number, y: number) => void;
  onCreateObject: (obj: Partial<BoardObject> & { id: string; type: any }) => void;
  onMoveObject: (id: string, x: number, y: number) => void;
  onResizeObject: (id: string, width: number, height: number, x?: number, y?: number) => void;
  onUpdateObject: (id: string, updates: Partial<BoardObject>) => void;
  onDeleteObject: (id: string) => void;
  onSelectObject: (id: string | null) => void;
  selectedObjectId: string | null;
}

type ResizeHandle = "nw" | "ne" | "se" | "sw" | "n" | "s" | "e" | "w";

export const BoardCanvas: React.FC<BoardCanvasProps> = ({
  objects,
  cursors,
  role,
  activeTool,
  selectedColor,
  zoom,
  onZoomChange,
  onSendCursor,
  onCreateObject,
  onMoveObject,
  onResizeObject,
  onUpdateObject,
  onDeleteObject,
  onSelectObject,
  selectedObjectId,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Viewport Pan
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 100, y: 100 });
  const [isPanning, setIsPanning] = useState(false);
  const [spacePressed, setSpacePressed] = useState(false);
  const startPanMouseRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const startPanPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Dragging / Moving Object
  const [isDraggingObject, setIsDraggingObject] = useState(false);
  const dragStartMouseRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const dragStartObjPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Resizing Object
  const [activeResizeHandle, setActiveResizeHandle] = useState<ResizeHandle | null>(null);
  const resizeStartMouseRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const resizeStartObjRef = useRef<{ x: number; y: number; width: number; height: number }>({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });

  // Inline Text Editing
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const isViewer = role === "VIEWER";

  // Spacebar pan detection
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && !editingId) {
        setSpacePressed(true);
      }
      if ((e.key === "Delete" || e.key === "Backspace") && selectedObjectId && !editingId && !isViewer) {
        onDeleteObject(selectedObjectId);
        onSelectObject(null);
      }
      if (e.key === "Escape") {
        if (editingId) setEditingId(null);
        else onSelectObject(null);
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") setSpacePressed(false);
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [editingId, selectedObjectId, isViewer, onDeleteObject, onSelectObject]);

  // Coordinate transforms
  const screenToBoard = useCallback(
    (screenX: number, screenY: number) => {
      if (!containerRef.current) return { x: 0, y: 0 };
      const rect = containerRef.current.getBoundingClientRect();
      return {
        x: (screenX - rect.left - pan.x) / zoom,
        y: (screenY - rect.top - pan.y) / zoom,
      };
    },
    [pan, zoom]
  );

  // Wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (!containerRef.current) return;

    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    const newZoom = Math.min(Math.max(zoom * zoomFactor, 0.2), 3.0);

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Center zoom on mouse point
    const newPanX = mouseX - (mouseX - pan.x) * (newZoom / zoom);
    const newPanY = mouseY - (mouseY - pan.y) * (newZoom / zoom);

    onZoomChange(newZoom);
    setPan({ x: newPanX, y: newPanY });
  };

  // Mouse Down
  const handleMouseDown = (e: React.MouseEvent) => {
    // Middle click or space pressed or pan tool -> Pan
    if (e.button === 1 || spacePressed || activeTool === "pan") {
      setIsPanning(true);
      startPanMouseRef.current = { x: e.clientX, y: e.clientY };
      startPanPosRef.current = { ...pan };
      return;
    }

    if (e.button !== 0) return; // Only left click

    const bCoord = screenToBoard(e.clientX, e.clientY);

    // If creating a new shape
    if (activeTool !== "select" && !isViewer) {
      const id = `obj_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
      const w = activeTool === "sticky_note" ? 180 : activeTool === "circle" ? 140 : 160;
      const h = activeTool === "sticky_note" ? 180 : activeTool === "circle" ? 140 : 100;

      onCreateObject({
        id,
        type: activeTool,
        x: Math.round(bCoord.x - w / 2),
        y: Math.round(bCoord.y - h / 2),
        width: w,
        height: h,
        color: activeTool === "sticky_note" ? selectedColor : "#ffffff",
        fill: activeTool === "sticky_note" ? selectedColor : "#1e293b",
        stroke: activeTool === "sticky_note" ? "transparent" : "#6366f1",
        stroke_width: 2,
        text: activeTool === "sticky_note" ? "New Idea" : activeTool === "text" ? "Type something..." : "",
      });
      onSelectObject(id);
      return;
    }

    // Clicking empty canvas clears selection and ends text editing
    onSelectObject(null);
    if (editingId) {
      onUpdateObject(editingId, { text: editText });
      setEditingId(null);
    }
  };

  // Mouse Move
  const handleMouseMove = (e: React.MouseEvent) => {
    const bCoord = screenToBoard(e.clientX, e.clientY);
    onSendCursor(Math.round(bCoord.x), Math.round(bCoord.y));

    if (isPanning) {
      const dx = e.clientX - startPanMouseRef.current.x;
      const dy = e.clientY - startPanMouseRef.current.y;
      setPan({
        x: startPanPosRef.current.x + dx,
        y: startPanPosRef.current.y + dy,
      });
      return;
    }

    if (isDraggingObject && selectedObjectId && !isViewer) {
      const dx = (e.clientX - dragStartMouseRef.current.x) / zoom;
      const dy = (e.clientY - dragStartMouseRef.current.y) / zoom;
      const newX = Math.round(dragStartObjPosRef.current.x + dx);
      const newY = Math.round(dragStartObjPosRef.current.y + dy);
      onMoveObject(selectedObjectId, newX, newY);
      return;
    }

    if (activeResizeHandle && selectedObjectId && !isViewer) {
      const dx = (e.clientX - resizeStartMouseRef.current.x) / zoom;
      const dy = (e.clientY - resizeStartMouseRef.current.y) / zoom;
      const s = resizeStartObjRef.current;

      let newW = s.width;
      let newH = s.height;
      let newX = s.x;
      let newY = s.y;

      if (activeResizeHandle.includes("e")) newW = Math.max(s.width + dx, 40);
      if (activeResizeHandle.includes("s")) newH = Math.max(s.height + dy, 40);
      if (activeResizeHandle.includes("w")) {
        const potentialW = s.width - dx;
        if (potentialW > 40) {
          newW = potentialW;
          newX = s.x + dx;
        }
      }
      if (activeResizeHandle.includes("n")) {
        const potentialH = s.height - dy;
        if (potentialH > 40) {
          newH = potentialH;
          newY = s.y + dy;
        }
      }

      onResizeObject(selectedObjectId, Math.round(newW), Math.round(newH), Math.round(newX), Math.round(newY));
    }
  };

  // Mouse Up
  const handleMouseUp = () => {
    setIsPanning(false);
    setIsDraggingObject(false);
    setActiveResizeHandle(null);
  };

  // Select object & start dragging
  const handleObjectMouseDown = (e: React.MouseEvent, obj: BoardObject) => {
    e.stopPropagation();

    if (isViewer || spacePressed || activeTool === "pan") return;

    onSelectObject(obj.id);
    setIsDraggingObject(true);
    dragStartMouseRef.current = { x: e.clientX, y: e.clientY };
    dragStartObjPosRef.current = { x: obj.x, y: obj.y };
  };

  // Double click object to edit text
  const handleObjectDoubleClick = (e: React.MouseEvent, obj: BoardObject) => {
    e.stopPropagation();
    if (isViewer) return;

    setEditingId(obj.id);
    setEditText(obj.text || "");
  };

  // Resize handle drag start
  const handleResizeHandleMouseDown = (e: React.MouseEvent, handle: ResizeHandle, obj: BoardObject) => {
    e.stopPropagation();
    if (isViewer) return;

    setActiveResizeHandle(handle);
    resizeStartMouseRef.current = { x: e.clientX, y: e.clientY };
    resizeStartObjRef.current = {
      x: obj.x,
      y: obj.y,
      width: obj.width,
      height: obj.height,
    };
  };

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      className={`w-full h-full relative overflow-hidden canvas-grid ${
        isPanning || spacePressed || activeTool === "pan"
          ? "cursor-grab active:cursor-grabbing"
          : activeTool !== "select"
          ? "cursor-crosshair"
          : "cursor-default"
      }`}
    >
      {/* Transformed Board World Layer */}
      <div
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: "0 0",
        }}
        className="absolute inset-0 pointer-events-none"
      >
        {/* Board Objects */}
        {objects.map((obj) => {
          const isSelected = selectedObjectId === obj.id;
          const isEditing = editingId === obj.id;

          return (
            <div
              key={obj.id}
              onMouseDown={(e) => handleObjectMouseDown(e, obj)}
              onDoubleClick={(e) => handleObjectDoubleClick(e, obj)}
              style={{
                transform: `translate(${obj.x}px, ${obj.y}px) rotate(${obj.rotation || 0}deg)`,
                width: `${obj.width}px`,
                height: `${obj.height}px`,
                zIndex: obj.z_index ?? 1,
              }}
              className="absolute pointer-events-auto select-none transition-shadow group"
            >
              {/* Sticky Note */}
              {obj.type === "sticky_note" && (
                <div
                  style={{ backgroundColor: obj.color || "#FEF08A" }}
                  className="w-full h-full rounded-xl p-4 shadow-xl border border-black/10 flex flex-col overflow-hidden text-slate-900"
                >
                  {isEditing ? (
                    <textarea
                      autoFocus
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onBlur={() => {
                        onUpdateObject(obj.id, { text: editText });
                        setEditingId(null);
                      }}
                      className="w-full h-full bg-transparent resize-none border-none outline-none font-medium text-sm leading-relaxed"
                    />
                  ) : (
                    <div className="w-full h-full font-medium text-sm leading-relaxed whitespace-pre-wrap break-words overflow-hidden">
                      {obj.text || "Double-click to write..."}
                    </div>
                  )}
                </div>
              )}

              {/* Rectangle Shape */}
              {obj.type === "rectangle" && (
                <div
                  style={{
                    backgroundColor: obj.fill || "#1e293b",
                    borderColor: obj.stroke || "#6366f1",
                    borderWidth: `${obj.stroke_width || 2}px`,
                  }}
                  className="w-full h-full rounded-xl shadow-lg flex items-center justify-center p-3 text-center"
                >
                  {isEditing ? (
                    <textarea
                      autoFocus
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onBlur={() => {
                        onUpdateObject(obj.id, { text: editText });
                        setEditingId(null);
                      }}
                      className="w-full h-full bg-transparent resize-none border-none outline-none text-white text-center font-semibold text-sm"
                    />
                  ) : (
                    <span className="text-white text-sm font-semibold whitespace-pre-wrap break-words">
                      {obj.text}
                    </span>
                  )}
                </div>
              )}

              {/* Circle Shape */}
              {obj.type === "circle" && (
                <div
                  style={{
                    backgroundColor: obj.fill || "#1e293b",
                    borderColor: obj.stroke || "#6366f1",
                    borderWidth: `${obj.stroke_width || 2}px`,
                  }}
                  className="w-full h-full rounded-full shadow-lg flex items-center justify-center p-4 text-center"
                >
                  {isEditing ? (
                    <textarea
                      autoFocus
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onBlur={() => {
                        onUpdateObject(obj.id, { text: editText });
                        setEditingId(null);
                      }}
                      className="w-full h-full bg-transparent resize-none border-none outline-none text-white text-center font-semibold text-sm flex items-center justify-center"
                    />
                  ) : (
                    <span className="text-white text-sm font-semibold whitespace-pre-wrap break-words">
                      {obj.text}
                    </span>
                  )}
                </div>
              )}

              {/* Text Box */}
              {obj.type === "text" && (
                <div className="w-full h-full p-2 flex items-center">
                  {isEditing ? (
                    <textarea
                      autoFocus
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onBlur={() => {
                        onUpdateObject(obj.id, { text: editText });
                        setEditingId(null);
                      }}
                      className="w-full h-full bg-transparent resize-none border-none outline-none text-white font-medium text-base leading-relaxed"
                    />
                  ) : (
                    <div className="text-white font-medium text-base leading-relaxed whitespace-pre-wrap break-words">
                      {obj.text || "Double-click to edit text"}
                    </div>
                  )}
                </div>
              )}

              {/* Selection Bounding Box & Handles */}
              {isSelected && !isViewer && (
                <div className="absolute -inset-1 border-2 border-indigo-500 rounded-lg pointer-events-none">
                  {/* Resize Handles: 4 corners + 4 edges */}
                  {(["nw", "ne", "se", "sw", "n", "s", "e", "w"] as ResizeHandle[]).map((h) => {
                    const handlePos: Record<ResizeHandle, string> = {
                      nw: "-top-1.5 -left-1.5 cursor-nwse-resize",
                      ne: "-top-1.5 -right-1.5 cursor-nesw-resize",
                      se: "-bottom-1.5 -right-1.5 cursor-nwse-resize",
                      sw: "-bottom-1.5 -left-1.5 cursor-nesw-resize",
                      n: "-top-1.5 left-1/2 -translate-x-1/2 cursor-ns-resize",
                      s: "-bottom-1.5 left-1/2 -translate-x-1/2 cursor-ns-resize",
                      e: "top-1/2 -right-1.5 -translate-y-1/2 cursor-ew-resize",
                      w: "top-1/2 -left-1.5 -translate-y-1/2 cursor-ew-resize",
                    };

                    return (
                      <div
                        key={h}
                        onMouseDown={(e) => handleResizeHandleMouseDown(e, h, obj)}
                        className={`absolute w-3 h-3 bg-white border-2 border-indigo-600 rounded-sm pointer-events-auto ${handlePos[h]}`}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* Live Remote Cursors Overlay */}
        {Object.entries(cursors).map(([uid, c]) => (
          <div
            key={uid}
            style={{
              transform: `translate(${c.x}px, ${c.y}px)`,
              transition: "transform 0.08s linear",
            }}
            className="absolute pointer-events-none z-50 flex items-start"
          >
            {/* SVG Mouse Pointer */}
            <svg
              className="w-4 h-4 drop-shadow-md"
              viewBox="0 0 24 24"
              fill={c.color || "#3B82F6"}
              stroke="#0f172a"
              strokeWidth="1.5"
            >
              <path d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87a.5.5 0 0 0 .35-.85L6.35 2.85a.5.5 0 0 0-.85.36z" />
            </svg>

            {/* Username pill */}
            <div
              style={{ backgroundColor: c.color || "#3B82F6" }}
              className="ml-1 px-2 py-0.5 rounded-full text-white text-[10px] font-bold shadow-md shadow-black/40 whitespace-nowrap"
            >
              {c.username}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
