import type { Board, BoardObject } from "../types/board";

export function exportBoardAsJson(boardInfo: Board | null, objects: BoardObject[]): void {
  const dataStr = JSON.stringify(
    {
      board: boardInfo,
      objects: objects.filter((o) => !o.is_deleted),
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

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxHeight: number
) {
  const words = text.split(" ");
  let line = "";
  let currentY = y;

  for (let n = 0; n < words.length; n++) {
    const testLine = line + words[n] + " ";
    const metrics = ctx.measureText(testLine);
    const testWidth = metrics.width;
    if (testWidth > maxWidth && n > 0) {
      if (currentY + lineHeight > y + maxHeight) {
        ctx.fillText(line.trim() + "...", x, currentY);
        return;
      }
      ctx.fillText(line, x, currentY);
      line = words[n] + " ";
      currentY += lineHeight;
    } else {
      line = testLine;
    }
  }
  if (currentY <= y + maxHeight) {
    ctx.fillText(line, x, currentY);
  }
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

export function exportBoardAsPng(boardInfo: Board | null, objects: BoardObject[]): void {
  const activeObjects = objects.filter((o) => !o.is_deleted);

  // Determine bounding dimensions
  let minX = 0;
  let minY = 0;
  let maxX = 1200;
  let maxY = 800;

  if (activeObjects.length > 0) {
    minX = Math.min(...activeObjects.map((o) => o.x));
    minY = Math.min(...activeObjects.map((o) => o.y));
    maxX = Math.max(...activeObjects.map((o) => o.x + o.width));
    maxY = Math.max(...activeObjects.map((o) => o.y + o.height));
  }

  const padding = 80;
  const contentWidth = Math.max(900, maxX - minX + padding * 2);
  const contentHeight = Math.max(650, maxY - minY + padding * 2);

  const canvas = document.createElement("canvas");
  canvas.width = contentWidth;
  canvas.height = contentHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Background
  ctx.fillStyle = "#020617"; // slate-950
  ctx.fillRect(0, 0, contentWidth, contentHeight);

  // Subtle grid lines
  ctx.strokeStyle = "rgba(51, 65, 85, 0.25)";
  ctx.lineWidth = 1;
  const gridSize = 40;
  for (let x = 0; x <= contentWidth; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, contentHeight);
    ctx.stroke();
  }
  for (let y = 0; y <= contentHeight; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(contentWidth, y);
    ctx.stroke();
  }

  // Draw Header / Watermark in canvas top-left
  ctx.fillStyle = "rgba(148, 163, 184, 0.7)";
  ctx.font = "bold 18px 'Inter', system-ui, sans-serif";
  ctx.fillText(boardInfo?.name || "Kanvaset Board", 30, 42);

  ctx.font = "12px 'Inter', system-ui, sans-serif";
  ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
  ctx.fillText(`Exported from Kanvaset · ${new Date().toLocaleDateString()}`, 30, 62);

  // Offset all objects so they are neatly placed
  const offsetX = padding - minX;
  const offsetY = padding - minY;

  const sortedObjects = [...activeObjects].sort((a, b) => (a.z_index ?? 1) - (b.z_index ?? 1));

  for (const obj of sortedObjects) {
    const rx = obj.x + offsetX;
    const ry = obj.y + offsetY;
    const rw = obj.width;
    const rh = obj.height;

    ctx.save();

    if (obj.type === "sticky_note") {
      // Sticky note shadow
      ctx.shadowColor = "rgba(0, 0, 0, 0.35)";
      ctx.shadowBlur = 14;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 6;

      // Body
      drawRoundedRect(ctx, rx, ry, rw, rh, 12);
      ctx.fillStyle = obj.color || "#FEF08A";
      ctx.fill();

      // Border
      ctx.shadowColor = "transparent";
      ctx.strokeStyle = "rgba(0,0,0,0.08)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Text
      if (obj.text) {
        ctx.fillStyle = "#0f172a"; // slate-900
        ctx.font = "500 14px 'Inter', system-ui, sans-serif";
        wrapText(ctx, obj.text, rx + 16, ry + 26, rw - 32, 20, rh - 36);
      }
    } else if (obj.type === "rectangle") {
      ctx.shadowColor = "rgba(0, 0, 0, 0.3)";
      ctx.shadowBlur = 10;
      ctx.shadowOffsetY = 4;

      drawRoundedRect(ctx, rx, ry, rw, rh, 12);
      ctx.fillStyle = obj.fill || "#1e293b";
      ctx.fill();

      ctx.shadowColor = "transparent";
      ctx.strokeStyle = obj.stroke || "#6366f1";
      ctx.lineWidth = obj.stroke_width || 2;
      ctx.stroke();

      if (obj.text) {
        ctx.fillStyle = "#f8fafc";
        ctx.font = "600 14px 'Inter', system-ui, sans-serif";
        wrapText(ctx, obj.text, rx + 14, ry + 24, rw - 28, 20, rh - 30);
      }
    } else if (obj.type === "circle") {
      ctx.shadowColor = "rgba(0, 0, 0, 0.3)";
      ctx.shadowBlur = 10;
      ctx.shadowOffsetY = 4;

      const centerX = rx + rw / 2;
      const centerY = ry + rh / 2;
      const radiusX = Math.abs(rw / 2);
      const radiusY = Math.abs(rh / 2);

      ctx.beginPath();
      ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, Math.PI * 2);
      ctx.fillStyle = obj.fill || "#1e293b";
      ctx.fill();

      ctx.shadowColor = "transparent";
      ctx.strokeStyle = obj.stroke || "#6366f1";
      ctx.lineWidth = obj.stroke_width || 2;
      ctx.stroke();

      if (obj.text) {
        ctx.fillStyle = "#f8fafc";
        ctx.font = "600 14px 'Inter', system-ui, sans-serif";
        wrapText(ctx, obj.text, rx + rw * 0.15, centerY - 8, rw * 0.7, 18, rh * 0.7);
      }
    } else if (obj.type === "text") {
      if (obj.text) {
        ctx.fillStyle = "#f8fafc";
        ctx.font = "500 16px 'Inter', system-ui, sans-serif";
        wrapText(ctx, obj.text, rx + 8, ry + 20, rw - 16, 22, rh - 20);
      }
    } else if (obj.type === "connector") {
      const startX = rx + 4;
      const startY = ry + rh / 2;
      const endX = rx + Math.max(rw - 12, 10);
      const endY = ry + rh / 2;

      ctx.strokeStyle = obj.stroke || "#6366f1";
      ctx.lineWidth = obj.stroke_width || 3;
      ctx.lineCap = "round";

      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      // Draw arrow head
      const angle = Math.atan2(endY - startY, endX - startX);
      const headLength = 10;
      ctx.fillStyle = obj.stroke || "#6366f1";
      ctx.beginPath();
      ctx.moveTo(endX + 8, endY);
      ctx.lineTo(endX - headLength * Math.cos(angle - Math.PI / 6), endY - headLength * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(endX - headLength * Math.cos(angle + Math.PI / 6), endY - headLength * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();
    }

    ctx.restore();
  }

  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${boardInfo?.name || "board"}_export.png`;
    a.click();
    URL.revokeObjectURL(url);
  }, "image/png");
}
