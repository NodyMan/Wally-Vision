'use client';
// The blink canvas: shows one frame of the active sequence, crisp pixels (no smoothing), zoom 1–8×, pan,
// and rings where the target is expected (target_xy) and where it was (target_xy_from).
// Keyboard: Space play/pause, ←/→ previous/next frame, +/− zoom, 0 reset.
// Controls live in PlayerControls.tsx; both read lib/store.ts and playback.ts.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { frameSrc, type BlinkFrame } from '@/lib/api/viewer';
import { useViewer } from '@/lib/store';
import { BlinkProgress } from './BlinkProgress';
import { clampPan, gridToScreen, layoutImage, screenToGrid, zoomAbout, type Point, type Size } from './geometry';
import { usePlayback, useSequence } from './playback';
import { pixToSky } from './wcs';

const RING_AFTER = '#7be36a';    // green: where the target should be in this frame
const RING_BEFORE = '#f5f5f5';   // white, dashed: where it was in the earlier epoch
const CLICK_SLOP_PX = 4;         // a pointer that moved less than this is a click, not a drag

function stepFrame(delta: number, count: number) {
  if (count < 1) return;
  const { frameIndex, setFrameIndex } = useViewer.getState();
  setFrameIndex((((Math.min(frameIndex, count - 1) + delta) % count) + count) % count);
}

export function BlinkPlayer() {
  const t = useTranslations('viewer');
  const blink = useViewer((s) => s.blink);
  const frameIndex = useViewer((s) => s.frameIndex);
  const zoom = useViewer((s) => s.zoom);
  const pan = useViewer((s) => s.pan);
  const selected = useViewer((s) => s.selected);
  const playing = usePlayback((s) => s.playing);
  const fps = usePlayback((s) => s.fps);
  const rings = usePlayback((s) => s.rings);
  const frames = useSequence();

  const boxRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const images = useRef(new Map<string, HTMLImageElement>());
  const [box, setBox] = useState<Size>({ width: 0, height: 0 });
  const [loaded, setLoaded] = useState(0);   // bumped when an image finishes loading, to redraw
  const countRef = useRef(0);                // the keyboard listener is bound once and reads the length here
  useEffect(() => {
    countRef.current = frames.length;
  }, [frames.length]);

  const grid: Size | null = blink ? { width: blink.grid.width, height: blink.grid.height } : null;
  const index = Math.min(frameIndex, Math.max(0, frames.length - 1));
  const frame: BlinkFrame | undefined = frames[index];

  // follow the size of the box
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setBox({ width: e.contentRect.width, height: e.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // preload every frame of the sequence so that blinking never waits for the network
  useEffect(() => {
    const keep = new Map<string, HTMLImageElement>();
    for (const f of frames) {
      let img = images.current.get(f.id);
      if (!img) {
        img = new Image();
        img.onload = () => setLoaded((n) => n + 1);
        img.src = frameSrc(f);
      }
      keep.set(f.id, img);
    }
    images.current = keep;
  }, [frames]);

  // a new response starts playing, unless the user asked the system for less motion
  useEffect(() => {
    if (!blink) return;
    const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    usePlayback.getState().setPlaying(!calm);
  }, [blink]);

  // the blink itself
  useEffect(() => {
    if (!playing || frames.length < 2) return;
    const id = window.setInterval(() => stepFrame(1, frames.length), 1000 / fps);
    return () => window.clearInterval(id);
  }, [playing, fps, frames.length]);

  // keep the frame inside the box when the box is resized
  useEffect(() => {
    if (!grid || !box.width) return;
    const p = clampPan(box, grid, zoom, pan);
    if (p.x !== pan.x || p.y !== pan.y) useViewer.getState().setPan(p);
  }, [box, grid?.width, grid?.height, zoom, pan]);  // eslint-disable-line react-hooks/exhaustive-deps

  // draw
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !box.width || !box.height) return;
    const dpr = window.devicePixelRatio || 1;
    const w = Math.round(box.width * dpr);
    const h = Math.round(box.height * dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, box.width, box.height);
    if (!grid || !frame) return;

    const l = layoutImage(box, grid, { zoom, pan });
    const img = images.current.get(frame.id);
    if (img?.complete && img.naturalWidth > 0) {
      ctx.imageSmoothingEnabled = false;   // each SPHEREx pixel (6.15″) stays a sharp square
      ctx.drawImage(img, l.left, l.top, grid.width * l.scale, grid.height * l.scale);
    }

    const ring = (xy: [number, number] | null | undefined, color: string, dashed: boolean) => {
      if (!xy) return;
      const c = gridToScreen(l, xy[0], xy[1]);
      ctx.beginPath();
      ctx.arc(c.x, c.y, Math.max(2.5 * l.scale, 12), 0, 2 * Math.PI);
      ctx.setLineDash(dashed ? [6, 5] : []);
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.setLineDash([]);
    };
    // a short tag with a leader line, like a callout on a chart; only on the pair frame, where both rings exist
    const tag = (xy: [number, number] | null | undefined, color: string, text: string, up: boolean) => {
      if (!xy) return;
      const c = gridToScreen(l, xy[0], xy[1]);
      const r = Math.max(2.5 * l.scale, 12);
      const x0 = c.x + r * 0.71, y0 = c.y + (up ? -r : r) * 0.71;
      const x1 = x0 + 26, y1 = y0 + (up ? -18 : 18);
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.lineTo(x1 + 8, y1);
      ctx.lineWidth = 1;
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.font = `10px ${getComputedStyle(canvas).fontFamily}`;
      ctx.textBaseline = 'middle';
      const w = ctx.measureText(text).width;
      ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
      ctx.fillRect(x1 + 10, y1 - 8, w + 8, 16);
      ctx.fillStyle = color;
      ctx.fillText(text, x1 + 14, y1 + 0.5);
    };
    if (rings) {
      ring(frame.target_xy_from, RING_BEFORE, true);
      ring(frame.target_xy, RING_AFTER, false);
      if (frame.target_xy_from) {
        tag(frame.target_xy_from, RING_BEFORE, t('rings.was'), false);
        tag(frame.target_xy, RING_AFTER, t('rings.now'), true);
      }
    }

    // measured centroids (small crosses) next to the predicted rings: the proof that the shift is real
    const m = frame.motion;
    if (rings && m) {
      const cross = (xy: [number, number], color: string) => {
        const c = gridToScreen(l, xy[0], xy[1]);
        const s = 5;
        ctx.beginPath();
        ctx.moveTo(c.x - s, c.y); ctx.lineTo(c.x + s, c.y);
        ctx.moveTo(c.x, c.y - s); ctx.lineTo(c.x, c.y + s);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = color;
        ctx.stroke();
      };
      cross(m.from_xy, RING_BEFORE);
      cross(m.to_xy, RING_AFTER);
    }

    if (selected) {   // the pixel picked by a click (#2 builds a spectrum for it)
      const c = gridToScreen(l, Math.round(selected.x), Math.round(selected.y));
      const half = l.scale / 2;
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = '#ffffff';
      ctx.strokeRect(c.x - half, c.y - half, l.scale, l.scale);
    }
  }, [box, grid?.width, grid?.height, frame, zoom, pan, rings, selected, loaded]);  // eslint-disable-line react-hooks/exhaustive-deps

  // wheel zoom needs a non-passive listener to stop the page from scrolling
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      const s = useViewer.getState();
      if (!s.blink) return;
      e.preventDefault();
      const r = el.getBoundingClientRect();
      const g = { width: s.blink.grid.width, height: s.blink.grid.height };
      const next = zoomAbout({ width: r.width, height: r.height }, g, { zoom: s.zoom, pan: s.pan },
        s.zoom * (e.deltaY < 0 ? 1.25 : 0.8), e.clientX - r.left, e.clientY - r.top);
      s.setZoom(next.zoom);
      s.setPan(next.pan);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      const tag = el?.tagName ?? '';
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el?.isContentEditable) return;
      const s = useViewer.getState();
      if (!s.blink) return;
      const p = usePlayback.getState();
      const count = countRef.current;
      const g = { width: s.blink.grid.width, height: s.blink.grid.height };
      const r = boxRef.current?.getBoundingClientRect();
      const zoomBy = (factor: number) => {
        if (!r) return;
        const next = zoomAbout({ width: r.width, height: r.height }, g, { zoom: s.zoom, pan: s.pan },
          s.zoom * factor, r.width / 2, r.height / 2);
        s.setZoom(next.zoom);
        s.setPan(next.pan);
      };
      if (e.key === ' ' || e.code === 'Space') {
        if (tag === 'BUTTON' || tag === 'A' || el?.getAttribute('role') === 'tab') return;  // Space presses those
        p.setPlaying(!p.playing);
      } else if (e.key === 'ArrowLeft') {
        p.setPlaying(false);
        stepFrame(-1, count);
      } else if (e.key === 'ArrowRight') {
        p.setPlaying(false);
        stepFrame(1, count);
      } else if (e.key === '+' || e.key === '=') {
        zoomBy(1.5);
      } else if (e.key === '-' || e.key === '_') {
        zoomBy(1 / 1.5);
      } else if (e.key === '0') {
        s.setZoom(1);
        s.setPan({ x: 0, y: 0 });
      } else {
        return;
      }
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // pointer: one finger or the mouse drags, two fingers pinch, a still press picks a pixel
  const pointers = useRef(new Map<number, Point>());
  const gesture = useRef<{ start: Point; pan: Point; moved: boolean; pinch: number } | null>(null);

  const local = (e: React.PointerEvent): Point => {
    const r = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!grid || e.button > 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const p = local(e);
    pointers.current.set(e.pointerId, p);
    const pts = [...pointers.current.values()];
    gesture.current = {
      start: p, pan, moved: pts.length > 1,
      pinch: pts.length === 2 ? Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) : 0,
    };
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    if (!g || !grid || !pointers.current.has(e.pointerId)) return;
    const p = local(e);
    pointers.current.set(e.pointerId, p);
    const s = useViewer.getState();
    const pts = [...pointers.current.values()];
    if (pts.length === 2 && g.pinch > 0) {
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      const next = zoomAbout(box, grid, { zoom: s.zoom, pan: s.pan }, s.zoom * (dist / g.pinch),
        (pts[0].x + pts[1].x) / 2, (pts[0].y + pts[1].y) / 2);
      g.pinch = dist;
      s.setZoom(next.zoom);
      s.setPan(next.pan);
      return;
    }
    const dx = p.x - g.start.x;
    const dy = p.y - g.start.y;
    if (!g.moved && Math.hypot(dx, dy) < CLICK_SLOP_PX) return;
    g.moved = true;
    s.setPan(clampPan(box, grid, s.zoom, { x: g.pan.x + dx, y: g.pan.y + dy }));
  };

  const onPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    const p = local(e);
    pointers.current.delete(e.pointerId);
    if (pointers.current.size > 0) {   // one finger of a pinch lifted: the other one must not jump the pan
      if (g) g.pinch = 0;
      return;
    }
    gesture.current = null;
    if (!g || g.moved || !grid || !blink || e.type === 'pointercancel') return;
    const px = screenToGrid(layoutImage(box, grid, { zoom, pan }), p.x, p.y);
    const x = Math.round(px.x);
    const y = Math.round(px.y);
    if (x < 0 || y < 0 || x >= grid.width || y >= grid.height) return;
    useViewer.getState().setSelected({ x, y, ...pixToSky(blink.grid, x, y) });
  };

  const label = frame
    ? t('player.frameLabel', { date: frame.date_iso, index: index + 1, total: frames.length })
    : t('player.label');

  return (
    <div ref={boxRef} className={`absolute inset-0 touch-none select-none ${grid ? 'cursor-grab active:cursor-grabbing' : ''}`}
         onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
      <canvas ref={canvasRef} role="img" aria-label={label} className="block h-full w-full font-mono" />

      {frame && (
        <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-2 text-xs">
          <span className="rounded-md bg-black/60 px-2 py-1 text-[11px] tabular-nums text-neutral-100">
            {frame.kind === 'diff_pair' && frame.pair
              ? t('player.pair', { from: frame.pair[0], to: frame.pair[1] })
              : frame.date_end_iso && frame.date_end_iso !== frame.date_iso
                ? t('player.dates', { from: frame.date_iso, to: frame.date_end_iso })
                : frame.date_iso}
            {frames.length > 1 && <span className="ml-2 opacity-70">{index + 1} / {frames.length}</span>}
          </span>
          {frame.target_wavelength_um != null && (
            <span className="rounded-md bg-black/60 px-2 py-1 text-[11px] tabular-nums text-neutral-100">
              {t('player.wavelength', { um: frame.target_wavelength_um.toFixed(2) })}
            </span>
          )}
        </div>
      )}

      {blink && frames.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center p-4 text-neutral-100">
          <p className="max-w-xs text-center text-sm opacity-80">{t('warnings.few_epochs')}</p>
        </div>
      )}
      {!blink && <BlinkProgress />}
    </div>
  );
}
