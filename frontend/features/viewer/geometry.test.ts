// npm test — pixel ↔ screen ↔ sky conversions (plan #1: "unit test of the centre and the corners").
// Developed with SI assistance (Claude); reviewed by team #1.
import { describe, expect, it } from 'vitest';
import type { BlinkGrid } from '@/lib/api/viewer';
import diff from '@/lib/mocks/blink_diff.json';
import { clampPan, gridToScreen, layoutImage, screenToGrid, zoomAbout } from './geometry';
import { buildQuery, parseView } from './viewUrl';
import { pixToSky, skyToPix } from './wcs';

const grid = diff.grid as unknown as BlinkGrid;
const box = { width: 490, height: 490 };
const size = { width: 49, height: 49 };

describe('geometry', () => {
  it('fits the frame at zoom 1 and puts pixel centres at integer coordinates', () => {
    const l = layoutImage(box, size, { zoom: 1, pan: { x: 0, y: 0 } });
    expect(l).toEqual({ scale: 10, left: 0, top: 0 });
    expect(gridToScreen(l, 24, 24)).toEqual({ x: 245, y: 245 });   // centre pixel → centre of the box
    expect(gridToScreen(l, 0, 0)).toEqual({ x: 5, y: 5 });         // pixel 0 covers 0..10 px
    expect(screenToGrid(l, 245, 245)).toEqual({ x: 24, y: 24 });
  });

  it('keeps the pixel under the cursor while zooming and clamps zoom to 1..8', () => {
    const view = { zoom: 1, pan: { x: 0, y: 0 } };
    const before = screenToGrid(layoutImage(box, size, view), 100, 380);
    const next = zoomAbout(box, size, view, 4, 100, 380);
    const after = screenToGrid(layoutImage(box, size, next), 100, 380);
    expect(after.x).toBeCloseTo(before.x, 9);
    expect(after.y).toBeCloseTo(before.y, 9);
    expect(zoomAbout(box, size, view, 99, 0, 0).zoom).toBe(8);
    expect(zoomAbout(box, size, next, 0.1, 0, 0)).toEqual({ zoom: 1, pan: { x: 0, y: 0 } });
  });

  it('does not let the frame leave the box', () => {
    expect(clampPan(box, size, 1, { x: 50, y: -50 })).toEqual({ x: 0, y: 0 });
    expect(clampPan(box, size, 2, { x: 999, y: -999 })).toEqual({ x: 245, y: -245 });
  });
});

describe('wcs', () => {
  const ra0 = grid.wcs_header.CRVAL1 as number;
  const dec0 = grid.wcs_header.CRVAL2 as number;

  it('maps the centre pixel to CRVAL', () => {
    const c = pixToSky(grid, 24, 24);
    expect(c.ra).toBeCloseTo(ra0, 9);
    expect(c.dec).toBeCloseTo(dec0, 9);
  });

  it('has north up and east to the left (canvas y goes down)', () => {
    expect(pixToSky(grid, 24, 0).dec).toBeGreaterThan(dec0);
    expect(pixToSky(grid, 0, 24).ra).toBeGreaterThan(ra0);
    // one pixel is 6.15″
    expect((pixToSky(grid, 24, 23).dec - dec0) * 3600).toBeCloseTo(6.15, 3);
  });

  it('round-trips the centre and the four corners', () => {
    for (const [x, y] of [[24, 24], [0, 0], [48, 0], [0, 48], [48, 48], [12.3, 7.8]]) {
      const s = pixToSky(grid, x, y);
      const p = skyToPix(grid, s.ra, s.dec);
      expect(p.x).toBeCloseTo(x, 6);
      expect(p.y).toBeCloseTo(y, 6);
    }
  });

  it('agrees with the backend (astropy) on the top-left and bottom-right pixels', () => {
    const tl = pixToSky(grid, 0, 0);
    const br = pixToSky(grid, 48, 48);
    expect(tl.ra).toBeCloseTo(EXPECTED.tl[0], 7);
    expect(tl.dec).toBeCloseTo(EXPECTED.tl[1], 7);
    expect(br.ra).toBeCloseTo(EXPECTED.br[0], 7);
    expect(br.dec).toBeCloseTo(EXPECTED.br[1], 7);
  });
});

describe('view URL', () => {
  it('round-trips a full link', () => {
    const q = 'ra=269.452083&dec=4.693364&name=Barnard%27s+Star&fov=300&mode=diff&det=2&t=1';
    const v = parseView(new URLSearchParams(q));
    expect(v).toEqual({ target: { ra: 269.452083, dec: 4.693364, name: "Barnard's Star" }, fov: 300, mode: 'diff', detector: 2, t: 1 });
    expect(buildQuery({ ...v, target: v.target! })).toBe(q);
  });

  it('falls back to safe defaults and never mixes bands in a difference', () => {
    expect(parseView(new URLSearchParams('ra=abc&dec=1')).target).toBeNull();
    expect(parseView(new URLSearchParams('ra=10&dec=95')).target).toBeNull();
    expect(parseView(new URLSearchParams('ra=10&dec=1&fov=99999&mode=x&det=9'))).toMatchObject({ fov: 300, mode: 'frames', detector: 6 });
    expect(parseView(new URLSearchParams('ra=10&dec=1&mode=diff&det=all')).detector).toBe(6);
    expect(parseView(new URLSearchParams('ra=10&dec=1&det=all')).detector).toBe('all');
  });
});

// computed with backend/core/grid.py: grid.pix_to_sky(WCS(Header(mock wcs_header)), x, y)
const EXPECTED = { tl: [269.4932233998547, 4.735189106878338], br: [269.4109474345763, 4.653189142010781] };
