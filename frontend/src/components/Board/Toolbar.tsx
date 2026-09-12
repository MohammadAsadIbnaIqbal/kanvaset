import React from "react";
import {
  Circle,
  Hand,
  MousePointer,
  MoveRight,
  Square,
  StickyNote,
  Trash2,
  Type,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import type { ObjectType } from "../../types/board";

export type ToolType = "select" | "pan" | ObjectType;

interface ToolbarProps {
  activeTool: ToolType;
  onSelectTool: (tool: ToolType) => void;
  selectedColor: string;
  onSelectColor: (color: string) => void;
  hasSelection: boolean;
  onDeleteSelection: () => void;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
  isViewer?: boolean;
}

const STICKY_COLORS = [
  "#FEF08A", // Yellow
  "#BAE6FD", // Blue
  "#BBF7D0", // Green
  "#FBCFE8", // Pink
  "#DDD6FE", // Purple
  "#FED7AA", // Orange
];

export const Toolbar: React.FC<ToolbarProps> = ({
  activeTool,
  onSelectTool,
  selectedColor,
  onSelectColor,
  hasSelection,
  onDeleteSelection,
  zoom,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  isViewer = false,
}) => {
  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-1.5 shadow-2xl flex items-center space-x-1.5 z-20 select-none">
      {/* Navigation Tools */}
      <button
        onClick={() => onSelectTool("select")}
        title="Select & Move (V)"
        className={`p-2 rounded-xl transition-all cursor-pointer ${
          activeTool === "select"
            ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
            : "text-slate-400 hover:text-white hover:bg-slate-800/80"
        }`}
      >
        <MousePointer className="w-4 h-4" />
      </button>

      <button
        onClick={() => onSelectTool("pan")}
        title="Pan Canvas (Space or Hand)"
        className={`p-2 rounded-xl transition-all cursor-pointer ${
          activeTool === "pan"
            ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
            : "text-slate-400 hover:text-white hover:bg-slate-800/80"
        }`}
      >
        <Hand className="w-4 h-4" />
      </button>

      {!isViewer && (
        <>
          <div className="w-px h-5 bg-slate-800 my-auto mx-1" />

          {/* Creation Tools */}
          <button
            onClick={() => onSelectTool("sticky_note")}
            title="Sticky Note (S)"
            className={`p-2 rounded-xl transition-all cursor-pointer ${
              activeTool === "sticky_note"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-slate-800/80"
            }`}
          >
            <StickyNote className="w-4 h-4" />
          </button>

          <button
            onClick={() => onSelectTool("rectangle")}
            title="Rectangle (R)"
            className={`p-2 rounded-xl transition-all cursor-pointer ${
              activeTool === "rectangle"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-slate-800/80"
            }`}
          >
            <Square className="w-4 h-4" />
          </button>

          <button
            onClick={() => onSelectTool("circle")}
            title="Circle (C)"
            className={`p-2 rounded-xl transition-all cursor-pointer ${
              activeTool === "circle"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-slate-800/80"
            }`}
          >
            <Circle className="w-4 h-4" />
          </button>

          <button
            onClick={() => onSelectTool("text")}
            title="Text Box (T)"
            className={`p-2 rounded-xl transition-all cursor-pointer ${
              activeTool === "text"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-slate-800/80"
            }`}
          >
            <Type className="w-4 h-4" />
          </button>

          <button
            onClick={() => onSelectTool("connector")}
            title="Connector / Arrow (L)"
            className={`p-2 rounded-xl transition-all cursor-pointer ${
              activeTool === "connector"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-slate-800/80"
            }`}
          >
            <MoveRight className="w-4 h-4" />
          </button>

          {/* Color Palettes for Sticky Notes / Shapes */}
          <div className="flex items-center space-x-1 pl-1 pr-1">
            {STICKY_COLORS.map((c) => (
              <button
                key={c}
                onClick={() => onSelectColor(c)}
                style={{ backgroundColor: c }}
                className={`w-4 h-4 rounded-full transition-transform cursor-pointer ${
                  selectedColor === c ? "ring-2 ring-indigo-400 scale-110" : "hover:scale-105"
                }`}
              />
            ))}
          </div>

          {hasSelection && (
            <>
              <div className="w-px h-5 bg-slate-800 my-auto mx-1" />
              <button
                onClick={onDeleteSelection}
                title="Delete Selected (Backspace / Delete)"
                className="p-2 rounded-xl text-rose-400 hover:text-white hover:bg-rose-500/80 transition-all cursor-pointer"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </>
      )}

      {/* Zoom Controls */}
      <div className="w-px h-5 bg-slate-800 my-auto mx-1" />

      <button
        onClick={onZoomOut}
        title="Zoom Out"
        className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer"
      >
        <ZoomOut className="w-4 h-4" />
      </button>

      <span
        onClick={onResetZoom}
        title="Reset Zoom to 100%"
        className="text-[11px] font-mono text-slate-400 px-1 hover:text-white cursor-pointer"
      >
        {Math.round(zoom * 100)}%
      </span>

      <button
        onClick={onZoomIn}
        title="Zoom In"
        className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
    </div>
  );
};
