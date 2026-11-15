"""
Astrophysical Verification Data & Reference Constants for SPHEREx Planet X Challenge.
Reference values compiled from the papers below; NOT independently re-checked by the team.
Check every number against the source before quoting it in the pitch.

References:
- Gaia DR3 (Gaia Collaboration et al. 2022 / 2023)
- CatWISE2020 (Eisenhardt et al. 2020; Marocco et al. 2021)
- Luhman (2014), Luhman & Esplin (2016), Kirkpatrick et al. (2021) for WISE 0855-0714
- McCaughrean et al. (2004) for Epsilon Indi Ba/Bb
- SPHEREx Instrument & Survey Specification (Crill et al. 2020, Doré et al. 2018)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class TargetAstroData:
    slug: str
    name: str
    target_type: str
    ra_deg: float
    dec_deg: float
    ref_epoch: float
    pmra_mas_yr: float
    pmdec_mas_yr: float
    parallax_mas: float | None
    distance_ly: float | None
    spectral_type: str
    temperature_k: float | None
    variability_period_days: float | None
    optimal_detector: int
    optimal_mode: str
    description: str


# 5 Contest Targets with verified astrophysical parameters
TARGETS: Dict[str, TargetAstroData] = {
    "barnards-star": TargetAstroData(
        slug="barnards-star",
        name="Barnard's Star (GJ 699)",
        target_type="high_pm_star",
        ra_deg=269.452083,
        dec_deg=4.693364,
        ref_epoch=2000.0,
        pmra_mas_yr=-801.6,
        pmdec_mas_yr=10362.4,
        parallax_mas=546.98,
        distance_ly=5.96,
        spectral_type="M4.0V",
        temperature_k=3130.0,
        variability_period_days=None,
        optimal_detector=2,
        optimal_mode="diff",
        description=(
            "Fastest proper motion star known (10.39″/yr). Over the ~26 years between J2000 "
            "and SPHEREx epoch (2025.9), it travels ~268″ north, requiring coordinate propagation "
            "to prevent centering cutouts on empty sky."
        ),
    ),
    "wise-0855": TargetAstroData(
        slug="wise-0855",
        name="WISE J085510.83−071442.5",
        target_type="brown_dwarf",
        ra_deg=133.79513,
        dec_deg=-7.24515,
        ref_epoch=2010.5,
        pmra_mas_yr=-8118.0,   # Luhman & Esplin (2016)
        pmdec_mas_yr=680.0,
        parallax_mas=448.0,
        distance_ly=7.27,
        spectral_type="Y2 / sub-brown dwarf",
        temperature_k=250.0,
        variability_period_days=None,
        optimal_detector=6,
        optimal_mode="diff",
        description=(
            "Coldest known brown dwarf (~250 K), free-floating planetary mass object (~3-10 M_Jup). "
            "Extreme proper motion (~8.09″/yr). Due to Wien's law and deep atmospheric absorption, "
            "it is undetected in D1-D3 and faint in D4; emission peaks in the 4.5-5.0 µm atmospheric window (D6)."
        ),
    ),
    "epsilon-indi-b": TargetAstroData(
        slug="epsilon-indi-b",
        name="Epsilon Indi Ba/Bb",
        target_type="brown_dwarf",
        ra_deg=331.04383,
        dec_deg=-56.78269,
        ref_epoch=2000.0,
        pmra_mas_yr=3961.0,
        pmdec_mas_yr=-2539.0,
        parallax_mas=274.84,
        distance_ly=11.87,
        spectral_type="T1 + T6 binary brown dwarfs",
        temperature_k=1100.0,
        variability_period_days=None,
        optimal_detector=6,
        optimal_mode="diff",
        description=(
            "Nearby binary brown dwarf system (projected separation 1459 AU from host star Eps Ind A). "
            "Shares host star common proper motion (~4.70″/yr). Exhibits prominent methane (CH4) "
            "and water (H2O) absorption in Band 4, and high signal-to-noise ratio in Band 6 (D6)."
        ),
    ),
    "rw-aurigae": TargetAstroData(
        slug="rw-aurigae",
        name="RW Aurigae (RW Aur)",
        target_type="variable_star",
        ra_deg=76.95642,
        dec_deg=30.40141,
        ref_epoch=2016.0,
        pmra_mas_yr=1.2,
        pmdec_mas_yr=-22.3,
        parallax_mas=6.16,
        distance_ly=520.0,
        spectral_type="CTTS (Classical T Tauri star binary)",
        temperature_k=4800.0,
        variability_period_days=None,
        optimal_detector=2,
        optimal_mode="frames",
        description=(
            "Young binary T Tauri star undergoing massive, irregular circumstellar dust occultations "
            "caused by tidal disruption from binary flybys. Stationary on SPHEREx pixel scale (<0.03″ shift); "
            "primary diagnostic is multi-epoch infrared variability and dust extinction."
        ),
    ),
    "r-draconis": TargetAstroData(
        slug="r-draconis",
        name="R Draconis (R Dra)",
        target_type="variable_star",
        ra_deg=248.16738,
        dec_deg=66.75489,
        ref_epoch=2016.0,
        pmra_mas_yr=-11.9,
        pmdec_mas_yr=-11.6,
        parallax_mas=1.85,
        distance_ly=1760.0,
        spectral_type="M4e-M8e Mira variable (AGB)",
        temperature_k=2800.0,
        variability_period_days=245.6,
        optimal_detector=2,
        optimal_mode="frames",
        description=(
            "Pulsating red giant Mira variable with a ~245.6-day period and ~6.5 magnitude optical swing. "
            "Located at high ecliptic latitude near North Ecliptic Pole, sampled on virtually every orbit "
            "(650+ SPHEREx exposures) providing dense, continuous light curve coverage."
        ),
    ),
}


@dataclass(frozen=True)
class SPHERExBand:
    detector: int
    wl_min_um: float
    wl_max_um: float
    resolving_power: str
    paired_with: int
    primary_targets: str


SPHEREX_BANDS: Dict[int, SPHERExBand] = {
    1: SPHERExBand(1, 0.746, 1.117, "R ~ 41", 4, "Near-IR stars, optical-IR transition"),
    2: SPHERExBand(2, 1.103, 1.650, "R ~ 41", 5, "Near-IR stellar photospheres, Barnard, RW Aur"),
    3: SPHERExBand(3, 1.630, 2.435, "R ~ 41", 6, "Dust, CO overtone (2.3 µm), CH4 overtones"),
    4: SPHERExBand(4, 2.403, 3.847, "R ~ 35-41", 1, "H2O ice/vapor (3.0 µm), CH4 fundamental (3.3 µm)"),
    5: SPHERExBand(5, 3.811, 4.430, "R ~ 110-130", 2, "CO2 asymmetric stretch (4.27 µm), cold photospheres"),
    6: SPHERExBand(6, 4.412, 5.010, "R ~ 110-130", 3, "CO fundamental (4.67 µm), peak flux for Y/T brown dwarfs"),
}


@dataclass(frozen=True)
class SpectralDiagnosticLine:
    key: str
    molecule: str
    wavelength_um: float
    band_detector: int
    band_name: str
    scientific_role: str


SPECTRAL_LINES: List[SpectralDiagnosticLine] = [
    SpectralDiagnosticLine(
        key="h2o",
        molecule="Water (H₂O)",
        wavelength_um=3.00,
        band_detector=4,
        band_name="Fundamental O-H stretching (ν₁, ν₃)",
        scientific_role=(
            "Pervasive absorption feature in cool stellar and brown dwarf atmospheres (M, L, T, Y dwarfs), "
            "planetary atmospheres, and circumstellar ice envelopes."
        ),
    ),
    SpectralDiagnosticLine(
        key="ch4",
        molecule="Methane (CH₄)",
        wavelength_um=3.30,
        band_detector=4,
        band_name="Fundamental C-H stretching (ν₃ band)",
        scientific_role=(
            "Defining spectroscopic fingerprint of cool brown dwarfs (T and Y dwarfs such as "
            "WISE 0855 and Epsilon Indi Ba/Bb) and giant gas planet atmospheres. Marks carbon conversion "
            "from CO to CH4 below ~1400 K."
        ),
    ),
    SpectralDiagnosticLine(
        key="co2",
        molecule="Carbon Dioxide (CO₂)",
        wavelength_um=4.27,
        band_detector=5,
        band_name="Fundamental asymmetric stretching (ν₃ band)",
        scientific_role=(
            "Key planetary atmosphere constituent, interstellar ice component, and exoplanet "
            "atmospheric biomarker tracer."
        ),
    ),
    SpectralDiagnosticLine(
        key="co",
        molecule="Carbon Monoxide (CO)",
        wavelength_um=4.67,
        band_detector=6,
        band_name="Fundamental 1-0 ro-vibrational band",
        scientific_role=(
            "Primary carbon-bearing molecule in high-temperature atmospheres (T > 1400 K), circumstellar "
            "accretion disks (RW Aurigae), cool giant photospheres, and Mira variables (R Draconis)."
        ),
    ),
]


def verify_target_astrometry(slug: str) -> dict:
    """Check astrometric displacement and mid-epoch coordinates for a contest target."""
    from .targets import ProperMotion, propagate

    target = TARGETS[slug]
    pm = ProperMotion(target.pmra_mas_yr, target.pmdec_mas_yr, target.ref_epoch)
    ra_prop, dec_prop = propagate(target.ra_deg, target.dec_deg, pm, 2025.9)
    total_pm_mas = (target.pmra_mas_yr**2 + target.pmdec_mas_yr**2)**0.5
    pixel_scale = 6.15  # arcsec/pixel
    dt = 2025.9 - target.ref_epoch
    shift_arcsec = (total_pm_mas * dt) / 1000.0
    shift_px = shift_arcsec / pixel_scale

    return {
        "slug": slug,
        "name": target.name,
        "catalog_coords": (target.ra_deg, target.dec_deg),
        "ref_epoch": target.ref_epoch,
        "propagated_coords_2025_9": (round(ra_prop, 6), round(dec_prop, 6)),
        "total_pm_arcsec_yr": round(total_pm_mas / 1000.0, 4),
        "shift_arcsec_to_2025_9": round(shift_arcsec, 2),
        "shift_pixels_to_2025_9": round(shift_px, 2),
        "annual_pixel_shift": round((total_pm_mas / 1000.0) / pixel_scale, 3),
    }
