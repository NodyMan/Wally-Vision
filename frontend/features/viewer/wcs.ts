// Frame pixel ↔ sky coordinates from grid.wcs_header (a TAN projection, see backend/core/grid.py).
//
// Astronomy note: a WCS header says which sky position each pixel shows. TAN ("gnomonic") is the
// usual flat projection for a small patch of sky. FITS counts pixels from 1 with y going UP,
// the canvas counts from 0 with y going DOWN — this file is the only place on the frontend that converts.
// Developed with SI assistance (Claude); reviewed by team #1.
import type { BlinkGrid } from '@/lib/api/viewer';

const RAD = Math.PI / 180;

function num(h: BlinkGrid['wcs_header'], key: string, fallback: number): number {
  const v = h[key];
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback;
}

/** Linear part of the WCS: pixel offsets → degrees on the tangent plane (CD matrix, or CDELT × PC). */
function matrix(h: BlinkGrid['wcs_header']): [number, number, number, number] {
  if (typeof h.CD1_1 === 'number') {
    return [num(h, 'CD1_1', 0), num(h, 'CD1_2', 0), num(h, 'CD2_1', 0), num(h, 'CD2_2', 0)];
  }
  const d1 = num(h, 'CDELT1', 1);
  const d2 = num(h, 'CDELT2', 1);
  return [d1 * num(h, 'PC1_1', 1), d1 * num(h, 'PC1_2', 0), d2 * num(h, 'PC2_1', 0), d2 * num(h, 'PC2_2', 1)];
}

/** Canvas pixel (0-based, y down) → { ra, dec } in degrees. */
export function pixToSky(grid: BlinkGrid, x: number, y: number): { ra: number; dec: number } {
  const h = grid.wcs_header;
  const [a, b, c, d] = matrix(h);
  const u = x + 1 - num(h, 'CRPIX1', (grid.width + 1) / 2);      // FITS x is 1-based
  const v = grid.height - y - num(h, 'CRPIX2', (grid.height + 1) / 2);  // FITS y is 1-based and flipped
  const xi = (a * u + b * v) * RAD;
  const eta = (c * u + d * v) * RAD;
  const ra0 = num(h, 'CRVAL1', 0) * RAD;
  const dec0 = num(h, 'CRVAL2', 0) * RAD;
  const denom = Math.cos(dec0) - eta * Math.sin(dec0);
  const ra = ra0 + Math.atan2(xi, denom);
  const dec = Math.atan2(Math.sin(dec0) + eta * Math.cos(dec0), Math.hypot(xi, denom));
  return { ra: (((ra / RAD) % 360) + 360) % 360, dec: dec / RAD };
}

/** { ra, dec } in degrees → canvas pixel (0-based, y down). */
export function skyToPix(grid: BlinkGrid, ra: number, dec: number): { x: number; y: number } {
  const h = grid.wcs_header;
  const [a, b, c, d] = matrix(h);
  const ra0 = num(h, 'CRVAL1', 0) * RAD;
  const dec0 = num(h, 'CRVAL2', 0) * RAD;
  const dra = ra * RAD - ra0;
  const cosc = Math.sin(dec0) * Math.sin(dec * RAD) + Math.cos(dec0) * Math.cos(dec * RAD) * Math.cos(dra);
  const xi = (Math.cos(dec * RAD) * Math.sin(dra)) / cosc / RAD;
  const eta = (Math.cos(dec0) * Math.sin(dec * RAD) - Math.sin(dec0) * Math.cos(dec * RAD) * Math.cos(dra)) / cosc / RAD;
  const det = a * d - b * c;
  const u = (d * xi - b * eta) / det;
  const v = (a * eta - c * xi) / det;
  return {
    x: u + num(h, 'CRPIX1', (grid.width + 1) / 2) - 1,
    y: grid.height - v - num(h, 'CRPIX2', (grid.height + 1) / 2),
  };
}
