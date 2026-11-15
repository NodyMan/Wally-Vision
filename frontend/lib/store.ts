// Общий стор (владелец #1). #2 и #3 добавляют поля через PR. Контракт: 00_COMMON.md §5.
// Developed with SI assistance (Claude); reviewed by team #1.
import { create } from 'zustand';
import type { BlinkJob, BlinkMode, BlinkResponse, DetectorParam } from './api/viewer';

export interface Target { ra: number; dec: number; name?: string }
export interface Selected { x: number; y: number; ra: number; dec: number }
export interface Overlays { gaia: boolean; catwise: boolean; badPixels: boolean; pmYears: number }

export interface ViewerState {
  target: Target | null;
  fov: number;
  mode: BlinkMode;
  detector: DetectorParam;            // по умолчанию 6 (4.4–5.0 мкм — там ярче всего коричневые карлики)
  frameIndex: number;
  zoom: number;                       // 1..8; 1 = whole frame fits the player
  pan: { x: number; y: number };     // shift of the frame centre, CSS pixels
  blink: BlinkResponse | null;
  job: Pick<BlinkJob, 'status' | 'progress' | 'stage'> | null;   // асинхронная загрузка
  error: string | null;               // машинный код → errors.<code>
  selected: Selected | null;          // клик по пикселю (#2 строит спектр)
  overlays: Overlays;                 // #2
  simpleMode: boolean;                // #3

  setTarget: (t: Target | null) => void;
  setFov: (fov: number) => void;
  setMode: (m: BlinkMode) => void;
  setDetector: (d: DetectorParam) => void;
  setFrameIndex: (i: number) => void;
  setZoom: (z: number) => void;
  setPan: (p: { x: number; y: number }) => void;
  setBlink: (b: BlinkResponse | null) => void;
  setJob: (j: ViewerState['job']) => void;
  setError: (e: string | null) => void;
  setSelected: (s: Selected | null) => void;
  setOverlays: (o: Partial<Overlays>) => void;
  setSimpleMode: (v: boolean) => void;
  toggleSimpleMode: () => void;
}

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

export const useViewer = create<ViewerState>((set) => ({
  target: null,
  fov: 300,
  mode: 'frames',
  detector: 6,
  frameIndex: 0,
  zoom: 1,
  pan: { x: 0, y: 0 },
  blink: null,
  job: null,
  error: null,
  selected: null,
  overlays: { gaia: false, catwise: false, badPixels: false, pmYears: 10 },
  simpleMode: true,

  // смена цели/параметров сбрасывает кадры и выбор, чтобы не показать старые данные
  setTarget: (target) => set({ target, blink: null, frameIndex: 0, selected: null, error: null, zoom: 1, pan: { x: 0, y: 0 } }),
  // setting the value that is already set must not drop the loaded frames: nothing would reload them
  setFov: (fov) => set((s) => s.fov === fov ? s : { fov, blink: null, frameIndex: 0, selected: null, error: null, zoom: 1, pan: { x: 0, y: 0 } }),
  // diff + all запрещён (COMMON): разные эпохи = разная смесь длин волн → ложные пятна
  setMode: (mode) => set((s) => s.mode === mode ? s : ({ mode, detector: mode === 'diff' && s.detector === 'all' ? 6 : s.detector,
                                   blink: null, frameIndex: 0, error: null })),
  setDetector: (detector) => set((s) => s.detector === detector ? s : ({ detector, mode: detector === 'all' && s.mode === 'diff' ? 'frames' : s.mode,
                                           blink: null, frameIndex: 0, error: null })),
  setFrameIndex: (frameIndex) => set({ frameIndex }),
  setZoom: (zoom) => set({ zoom: clamp(zoom, 1, 8) }),
  setPan: (pan) => set({ pan }),
  setBlink: (blink) => set({ blink, frameIndex: 0, job: null }),
  setJob: (job) => set({ job }),
  setError: (error) => set({ error, job: null }),
  setSelected: (selected) => set({ selected }),
  setOverlays: (o) => set((s) => ({ overlays: { ...s.overlays, ...o } })),
  setSimpleMode: (simpleMode) => set({ simpleMode }),
  toggleSimpleMode: () => set((s) => ({ simpleMode: !s.simpleMode })),
}));
