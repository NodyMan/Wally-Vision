"use client";

import { useViewer } from "@/lib/store";

/**
 * Shared Simple Mode state (#3), now bridged into #1's `lib/store.ts` as its comment asked:
 * there is one flag, so the header switch, the home page and the viewer always agree.
 * Default is true so beginners see a clean, uncluttered interface first.
 * Usage stays the same: `useSimpleModeStore((s) => s.simpleMode)` / `s.toggleSimpleMode`.
 */
export const useSimpleModeStore = useViewer;
