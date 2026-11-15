'use client';
// Player-only state (play/pause, speed, rings, which diff frames to show) and the active frame sequence.
// It is kept out of lib/store.ts because nobody outside the player needs it.
// Developed with SI assistance (Claude); reviewed by team #1.
import { useMemo } from 'react';
import { create } from 'zustand';
import { framesFor, type BlinkFrame, type BlinkResponse, type Detector, type DetectorParam, type FrameKind } from '@/lib/api/viewer';
import { useViewer } from '@/lib/store';

export type DiffView = 'pair' | 'epochs';   // pair: latest minus earliest; epochs: each epoch minus the median
export const SPEEDS_FPS = [0.5, 1, 2, 3, 5] as const;

interface PlaybackState {
  playing: boolean;
  fps: number;
  rings: boolean;
  diffView: DiffView;
  band: Detector | null;        // which band to show when detector = 'all' (bands are never mixed)
  setPlaying: (v: boolean) => void;
  setFps: (v: number) => void;
  setRings: (v: boolean) => void;
  setDiffView: (v: DiffView) => void;
  setBand: (v: Detector | null) => void;
}

export const usePlayback = create<PlaybackState>((set) => ({
  playing: false,
  fps: 2,
  rings: true,
  diffView: 'pair',
  band: null,
  setPlaying: (playing) => set({ playing }),
  setFps: (fps) => set({ fps }),
  setRings: (rings) => set({ rings }),
  setDiffView: (diffView) => set({ diffView }),
  setBand: (band) => set({ band }),
}));

/** Bands present in the response, in order. */
export function bandsOf(blink: BlinkResponse | null): Detector[] {
  return blink ? Array.from(new Set(blink.frames.map((f) => f.detector))).sort() : [];
}

/** The one time sequence to show: a single detector and a single kind of frame. */
export function sequenceOf(blink: BlinkResponse | null, detector: DetectorParam, band: Detector | null,
                           diffView: DiffView): BlinkFrame[] {
  if (!blink) return [];
  const bands = bandsOf(blink);
  const det = detector === 'all' ? (band && bands.includes(band) ? band : bands[0]) : detector;
  if (det === undefined) return [];
  const kinds: FrameKind[] = blink.mode === 'frames' ? ['epoch']
    : blink.mode === 'sum' ? ['sum']
    : diffView === 'pair' ? ['diff_pair'] : ['diff_vs_median'];
  const frames = framesFor(blink, det, kinds);
  // an old response without a pair frame still shows something in diff mode
  return frames.length || blink.mode !== 'diff' ? frames : framesFor(blink, det, ['diff_vs_median']);
}

export function useSequence(): BlinkFrame[] {
  const blink = useViewer((s) => s.blink);
  const detector = useViewer((s) => s.detector);
  const band = usePlayback((s) => s.band);
  const diffView = usePlayback((s) => s.diffView);
  return useMemo(() => sequenceOf(blink, detector, band, diffView), [blink, detector, band, diffView]);
}
