// Where the frame sits inside the player box, and how screen points map to frame pixels.
//
// Conventions (COMMON §6): frame pixels are 0-based, origin top-left, y down, and an integer
// coordinate is the CENTRE of a pixel (target_xy = [24, 24] is the middle of pixel 24 in a 49 px frame).
// zoom 1 fits the whole frame into the box; pan is the shift of the frame centre in CSS pixels.
// Developed with SI assistance (Claude); reviewed by team #1.

export interface Size { width: number; height: number }
export interface Point { x: number; y: number }
export interface View { zoom: number; pan: Point }
/** scale: CSS pixels per frame pixel; left/top: CSS position of the frame's top-left corner. */
export interface ImageLayout { scale: number; left: number; top: number }

export const ZOOM_MIN = 1;
export const ZOOM_MAX = 8;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v)) + 0;   // + 0 turns -0 into 0

function fitScale(box: Size, grid: Size): number {
  return Math.min(box.width / grid.width, box.height / grid.height);
}

export function layoutImage(box: Size, grid: Size, view: View): ImageLayout {
  const scale = fitScale(box, grid) * view.zoom;
  return {
    scale,
    left: box.width / 2 + view.pan.x - (grid.width * scale) / 2,
    top: box.height / 2 + view.pan.y - (grid.height * scale) / 2,
  };
}

export function gridToScreen(l: ImageLayout, x: number, y: number): Point {
  return { x: l.left + (x + 0.5) * l.scale, y: l.top + (y + 0.5) * l.scale };
}

export function screenToGrid(l: ImageLayout, sx: number, sy: number): Point {
  return { x: (sx - l.left) / l.scale - 0.5, y: (sy - l.top) / l.scale - 0.5 };
}

/** Keeps the frame from being dragged out of the box: no pan at zoom 1, edges stay glued when zoomed. */
export function clampPan(box: Size, grid: Size, zoom: number, pan: Point): Point {
  const scale = fitScale(box, grid) * zoom;
  const maxX = Math.max(0, (grid.width * scale - box.width) / 2);
  const maxY = Math.max(0, (grid.height * scale - box.height) / 2);
  return { x: clamp(pan.x, -maxX, maxX), y: clamp(pan.y, -maxY, maxY) };
}

/** Zooms so that the frame pixel under the screen point (sx, sy) stays under it. */
export function zoomAbout(box: Size, grid: Size, view: View, nextZoom: number, sx: number, sy: number): View {
  const zoom = clamp(nextZoom, ZOOM_MIN, ZOOM_MAX);
  const k = zoom / view.zoom;
  const dx = sx - box.width / 2;
  const dy = sy - box.height / 2;
  const pan = { x: dx - (dx - view.pan.x) * k, y: dy - (dy - view.pan.y) * k };
  return { zoom, pan: clampPan(box, grid, zoom, pan) };
}
