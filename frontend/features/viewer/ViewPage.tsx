'use client';
// The /view page: URL → store → blink request → player. The URL always describes the current view,
// so a copied link reopens the same target, field of view, mode, band and (when paused) frame.
//   /view?ra=269.452083&dec=4.693364&name=Barnard%27s+Star&fov=300&mode=diff&det=2&t=1
// The page URL says `det`; the API call says `detector` (COMMON §6).
// Developed with SI assistance (Claude); reviewed by team #1.
import { useEffect, useRef, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { useViewer } from '@/lib/store';
import { BlinkPlayer } from './BlinkPlayer';
import { EpochTimeline } from './EpochTimeline';
import { PlayerControls } from './PlayerControls';
import { usePlayback, useSequence } from './playback';
import { useBlink } from './useBlink';
import { ViewerLayout, type ViewerLayoutProps } from './ViewerLayout';
import { ViewerNotes } from './ViewerNotes';
import { ViewerReadout } from './ViewerReadout';
import { ViewerToolbar } from './ViewerToolbar';
import { buildQuery, parseView } from './viewUrl';

/** Slots for teammates: #2 passes overlay / toolbarExtra / tabs, #3 passes actions and tabs. */
export type ViewPageSlots = Pick<ViewerLayoutProps,
  'overlay' | 'toolbarExtra' | 'actions' | 'sidePanel' | 'bottomTabs' | 'compact'>;

export function ViewPage(slots: ViewPageSlots) {
  const search = useSearchParams();
  const pathname = usePathname();
  const { target, fov, mode, detector, frameIndex, blink } = useViewer();
  const playing = usePlayback((s) => s.playing);
  const frames = useSequence();
  const [ready, setReady] = useState(false);
  const written = useRef<string | null>(null);   // the query this page wrote last, to tell it from a navigation
  const pendingT = useRef<number | null>(null);  // frame from the link, applied once the frames arrive

  useBlink();

  // URL → store (first load, and navigation to another target while the page stays mounted)
  const query = search.toString();
  useEffect(() => {
    if (query === written.current) return;
    const v = parseView(new URLSearchParams(query));
    const s = useViewer.getState();
    const same = s.target?.ra === v.target?.ra && s.target?.dec === v.target?.dec && s.target?.name === v.target?.name
      && s.fov === v.fov && s.mode === v.mode && s.detector === v.detector && (s.target === null) === (v.target === null);
    pendingT.current = v.t;
    if (!same) {
      useViewer.setState({ target: v.target, fov: v.fov, mode: v.mode, detector: v.detector,
                           blink: null, frameIndex: 0, selected: null, error: null, zoom: 1, pan: { x: 0, y: 0 } });
    }
    setReady(true);
  }, [query]);

  // a link with ?t= opens on that frame, paused (runs after the player's own autoplay effect)
  useEffect(() => {
    if (!blink || pendingT.current === null || frames.length === 0) return;
    useViewer.getState().setFrameIndex(Math.min(pendingT.current, frames.length - 1));
    usePlayback.getState().setPlaying(false);
    pendingT.current = null;
  }, [blink, frames.length]);

  // store → URL, without a navigation or a reload; the frame is written only while paused
  useEffect(() => {
    if (!ready || !target) return;
    const t = blink && !playing && frames.length > 1 ? Math.min(frameIndex, frames.length - 1) : pendingT.current;
    const next = buildQuery({ target, fov, mode, detector, t });
    if (next === window.location.search.replace(/^\?/, '')) {
      written.current = next;
      return;
    }
    written.current = next;
    window.history.replaceState(null, '', `${pathname}?${next}`);
  }, [ready, target, fov, mode, detector, frameIndex, playing, blink, frames.length, pathname]);

  return (
    <ViewerLayout
      player={<BlinkPlayer />}
      controls={<><PlayerControls /><EpochTimeline /><ViewerNotes /></>}
      toolbar={<ViewerToolbar />}
      {...slots}
      sidePanel={<>{slots.sidePanel}<ViewerReadout /></>}
    />
  );
}
