"""
Unit tests for Astrophysical verification of contest targets, SPHEREx bands, and LVF lines.
"""
from __future__ import annotations

import pytest

from core import astro_verify, config


def test_five_contest_targets_present():
    expected = {"barnards-star", "wise-0855", "epsilon-indi-b", "rw-aurigae", "r-draconis"}
    assert set(astro_verify.TARGETS.keys()) == expected


def test_target_coordinates_and_proper_motions():
    # Barnard's Star
    bs = astro_verify.TARGETS["barnards-star"]
    assert bs.ra_deg == pytest.approx(269.452083, abs=0.0001)
    assert bs.dec_deg == pytest.approx(4.693364, abs=0.0001)
    assert bs.pmra_mas_yr == pytest.approx(-801.6, abs=0.1)
    assert bs.pmdec_mas_yr == pytest.approx(10362.4, abs=0.1)
    assert bs.distance_ly == pytest.approx(5.96, abs=0.05)

    # WISE 0855-0714
    w = astro_verify.TARGETS["wise-0855"]
    assert w.ra_deg == pytest.approx(133.79513, abs=0.0001)
    assert w.dec_deg == pytest.approx(-7.24515, abs=0.0001)
    assert w.pmra_mas_yr == pytest.approx(-8118.0, abs=1.0)
    assert w.pmdec_mas_yr == pytest.approx(680.0, abs=1.0)
    assert w.temperature_k == pytest.approx(250.0, abs=20.0)

    # Epsilon Indi Ba/Bb
    ei = astro_verify.TARGETS["epsilon-indi-b"]
    assert ei.ra_deg == pytest.approx(331.04383, abs=0.0001)
    assert ei.dec_deg == pytest.approx(-56.78269, abs=0.0001)
    assert ei.pmra_mas_yr == pytest.approx(3961.0, abs=1.0)
    assert ei.pmdec_mas_yr == pytest.approx(-2539.0, abs=1.0)

    # RW Aurigae
    rw = astro_verify.TARGETS["rw-aurigae"]
    assert rw.ra_deg == pytest.approx(76.95642, abs=0.0001)
    assert rw.dec_deg == pytest.approx(30.40141, abs=0.0001)
    assert rw.target_type == "variable_star"

    # R Draconis
    rd = astro_verify.TARGETS["r-draconis"]
    assert rd.ra_deg == pytest.approx(248.16738, abs=0.0001)
    assert rd.dec_deg == pytest.approx(66.75489, abs=0.0001)
    assert rd.variability_period_days == pytest.approx(245.6, abs=1.0)


def test_spherex_detector_bands():
    bands = astro_verify.SPHEREX_BANDS
    assert len(bands) == 6
    assert bands[1].wl_min_um <= 0.75 and bands[1].wl_max_um >= 1.11
    assert bands[2].wl_min_um <= 1.11 and bands[2].wl_max_um >= 1.64
    assert bands[3].wl_min_um <= 1.64 and bands[3].wl_max_um >= 2.43
    assert bands[4].wl_min_um <= 2.41 and bands[4].wl_max_um >= 3.84
    assert bands[5].wl_min_um <= 3.82 and bands[5].wl_max_um >= 4.42
    assert bands[6].wl_min_um <= 4.42 and bands[6].wl_max_um >= 5.00

    # Dichroic pairs
    assert bands[1].paired_with == 4
    assert bands[2].paired_with == 5
    assert bands[3].paired_with == 6


def test_spectral_diagnostic_lines():
    lines = {line.key: line for line in astro_verify.SPECTRAL_LINES}
    assert set(lines.keys()) == {"h2o", "ch4", "co2", "co"}

    assert lines["h2o"].wavelength_um == 3.00
    assert lines["h2o"].band_detector == 4

    assert lines["ch4"].wavelength_um == 3.30
    assert lines["ch4"].band_detector == 4

    assert lines["co2"].wavelength_um == 4.27
    assert lines["co2"].band_detector == 5

    assert lines["co"].wavelength_um == 4.67
    assert lines["co"].band_detector == 6


def test_astrometry_propagation():
    res = astro_verify.verify_target_astrometry("barnards-star")
    # In 25.9 yr, Barnard shifts ~268" north (~43 pixels at 6.15"/px)
    assert res["shift_arcsec_to_2025_9"] > 260.0
    assert res["shift_pixels_to_2025_9"] > 40.0
    assert res["propagated_coords_2025_9"][1] > res["catalog_coords"][1]  # moves North
