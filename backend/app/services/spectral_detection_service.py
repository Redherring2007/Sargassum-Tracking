from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.models.domain import SargassumObservation

RED_WAVELENGTH_NM = 665.0
NIR_WAVELENGTH_NM = 842.0
SWIR_WAVELENGTH_NM = 1610.0

BandGrid = list[list[float]]
MaskGrid = list[list[bool]]


@dataclass(frozen=True)
class SpectralPixel:
    row: int
    col: int
    red: float
    nir: float
    swir: float
    ndvi: float
    fai: float
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class SpectralDetectionThresholds:
    min_fai: float = 0.012
    min_ndvi: float = 0.05
    max_swir: float = 0.35
    min_nir: float = 0.04


@dataclass(frozen=True)
class RasterGridDefinition:
    origin_latitude: float = 13.4
    origin_longitude: float = -59.2
    pixel_size_degrees: float = 0.01


class Sentinel2BandAdapter(Protocol):
    def load_bands(self) -> tuple[BandGrid, BandGrid, BandGrid]:
        """Return Sentinel-2 compatible B4/B8/B11 reflectance grids."""


class MockSentinel2BandAdapter:
    """Small no-network Sentinel-2-style fixture for local spectral pipeline demos."""

    def load_bands(self) -> tuple[BandGrid, BandGrid, BandGrid]:
        red = [
            [0.035, 0.036, 0.034, 0.033, 0.035],
            [0.034, 0.045, 0.047, 0.035, 0.034],
            [0.033, 0.046, 0.050, 0.044, 0.033],
            [0.034, 0.036, 0.045, 0.043, 0.034],
            [0.035, 0.034, 0.033, 0.034, 0.035],
        ]
        nir = [
            [0.040, 0.041, 0.040, 0.039, 0.040],
            [0.039, 0.085, 0.090, 0.043, 0.040],
            [0.040, 0.088, 0.096, 0.083, 0.039],
            [0.039, 0.043, 0.086, 0.081, 0.040],
            [0.040, 0.039, 0.038, 0.039, 0.040],
        ]
        swir = [
            [0.030, 0.031, 0.030, 0.030, 0.031],
            [0.030, 0.048, 0.049, 0.033, 0.031],
            [0.030, 0.047, 0.052, 0.046, 0.030],
            [0.031, 0.033, 0.047, 0.045, 0.031],
            [0.030, 0.030, 0.030, 0.030, 0.030],
        ]
        return red, nir, swir


class SpectralDetectionService:
    """Sentinel-2-compatible spectral detector for floating sargassum candidates.

    The service operates on local B4/B8/B11 reflectance grids first. A future
    Copernicus/Sentinel adapter can implement `Sentinel2BandAdapter` and supply
    atmospherically corrected reflectance arrays without changing downstream
    thresholding, GeoJSON, or observation conversion logic.
    """

    red_wavelength_nm = RED_WAVELENGTH_NM
    nir_wavelength_nm = NIR_WAVELENGTH_NM
    swir_wavelength_nm = SWIR_WAVELENGTH_NM

    def safe_divide(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        if abs(denominator) < 1e-12:
            return default
        return numerator / denominator

    def calculate_ndvi(self, red: float, nir: float) -> float:
        return self.safe_divide(nir - red, nir + red)

    def calculate_fai(self, red: float, nir: float, swir: float) -> float:
        wavelength_ratio = (self.nir_wavelength_nm - self.red_wavelength_nm) / (
            self.swir_wavelength_nm - self.red_wavelength_nm
        )
        baseline = red + (swir - red) * wavelength_ratio
        return nir - baseline

    def detect_likely_sargassum_pixels(
        self,
        red_band: BandGrid,
        nir_band: BandGrid,
        swir_band: BandGrid,
        thresholds: SpectralDetectionThresholds | None = None,
    ) -> tuple[MaskGrid, list[SpectralPixel]]:
        thresholds = thresholds or SpectralDetectionThresholds()
        self._validate_bands(red_band, nir_band, swir_band)
        mask: MaskGrid = []
        pixels: list[SpectralPixel] = []
        for row_index, red_row in enumerate(red_band):
            mask_row: list[bool] = []
            for col_index, red in enumerate(red_row):
                nir = nir_band[row_index][col_index]
                swir = swir_band[row_index][col_index]
                ndvi = self.calculate_ndvi(red, nir)
                fai = self.calculate_fai(red, nir, swir)
                detected = (
                    fai >= thresholds.min_fai
                    and ndvi >= thresholds.min_ndvi
                    and swir <= thresholds.max_swir
                    and nir >= thresholds.min_nir
                )
                mask_row.append(detected)
                if detected:
                    pixels.append(
                        SpectralPixel(
                            row=row_index,
                            col=col_index,
                            red=red,
                            nir=nir,
                            swir=swir,
                            ndvi=round(ndvi, 6),
                            fai=round(fai, 6),
                        )
                    )
            mask.append(mask_row)
        return mask, pixels

    def georeference_pixels(
        self, pixels: list[SpectralPixel], grid: RasterGridDefinition | None = None
    ) -> list[SpectralPixel]:
        grid = grid or RasterGridDefinition()
        georeferenced: list[SpectralPixel] = []
        for pixel in pixels:
            latitude = grid.origin_latitude - pixel.row * grid.pixel_size_degrees
            longitude = grid.origin_longitude + pixel.col * grid.pixel_size_degrees
            georeferenced.append(
                SpectralPixel(
                    row=pixel.row,
                    col=pixel.col,
                    red=pixel.red,
                    nir=pixel.nir,
                    swir=pixel.swir,
                    ndvi=pixel.ndvi,
                    fai=pixel.fai,
                    latitude=round(latitude, 6),
                    longitude=round(longitude, 6),
                )
            )
        return georeferenced

    def detections_to_geojson_features(self, pixels: list[SpectralPixel]) -> list[dict]:
        features = []
        for pixel in pixels:
            if pixel.latitude is None or pixel.longitude is None:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [pixel.longitude, pixel.latitude]},
                    "properties": {
                        "row": pixel.row,
                        "col": pixel.col,
                        "ndvi": pixel.ndvi,
                        "fai": pixel.fai,
                        "red": pixel.red,
                        "nir": pixel.nir,
                        "swir": pixel.swir,
                        "source_type": "sentinel2_spectral_detection",
                    },
                }
            )
        return features

    def summarise_detection_confidence(self, pixels: list[SpectralPixel], total_pixels: int) -> dict:
        detected_count = len(pixels)
        if detected_count == 0:
            return {
                "detected_pixels": 0,
                "total_pixels": total_pixels,
                "coverage_ratio": 0.0,
                "density_level": "none",
                "confidence_score": 0.0,
                "mean_ndvi": 0.0,
                "mean_fai": 0.0,
            }
        coverage_ratio = self.safe_divide(detected_count, total_pixels)
        mean_ndvi = sum(pixel.ndvi for pixel in pixels) / detected_count
        mean_fai = sum(pixel.fai for pixel in pixels) / detected_count
        density_level = self._density_level(coverage_ratio)
        confidence = min(0.92, 0.45 + min(0.3, coverage_ratio * 3.0) + min(0.17, mean_fai * 5.0))
        return {
            "detected_pixels": detected_count,
            "total_pixels": total_pixels,
            "coverage_ratio": round(coverage_ratio, 4),
            "density_level": density_level,
            "confidence_score": round(confidence, 3),
            "mean_ndvi": round(mean_ndvi, 4),
            "mean_fai": round(mean_fai, 5),
        }

    def detections_to_observations(
        self,
        pixels: list[SpectralPixel],
        summary: dict,
        source_reference: str = "sentinel2_mock_spectral_demo",
    ) -> list[SargassumObservation]:
        observations: list[SargassumObservation] = []
        for pixel in pixels:
            if pixel.latitude is None or pixel.longitude is None:
                continue
            observations.append(
                SargassumObservation(
                    latitude=pixel.latitude,
                    longitude=pixel.longitude,
                    observed_at=datetime.now(UTC),
                    source_type="sentinel2_spectral_detection",
                    source_reference=f"{source_reference}:r{pixel.row}:c{pixel.col}",
                    density_level=summary["density_level"],
                    estimated_area_m2=100.0,
                    confidence_score=summary["confidence_score"],
                    notes=f"Sentinel-2-compatible spectral candidate NDVI={pixel.ndvi}, FAI={pixel.fai}",
                )
            )
        return observations

    def run_detection(
        self,
        red_band: BandGrid,
        nir_band: BandGrid,
        swir_band: BandGrid,
        grid: RasterGridDefinition | None = None,
        thresholds: SpectralDetectionThresholds | None = None,
    ) -> dict:
        mask, pixels = self.detect_likely_sargassum_pixels(red_band, nir_band, swir_band, thresholds)
        georeferenced = self.georeference_pixels(pixels, grid)
        total_pixels = len(red_band) * len(red_band[0]) if red_band else 0
        summary = self.summarise_detection_confidence(georeferenced, total_pixels)
        return {
            "algorithm": "sentinel2_ndvi_fai_threshold",
            "bands": {
                "B4_red_nm": self.red_wavelength_nm,
                "B8_nir_nm": self.nir_wavelength_nm,
                "B11_swir_nm": self.swir_wavelength_nm,
            },
            "thresholds": (thresholds or SpectralDetectionThresholds()).__dict__,
            "mask": mask,
            "summary": summary,
            "features": self.detections_to_geojson_features(georeferenced),
        }

    def run_mock_detection(self) -> dict:
        red, nir, swir = MockSentinel2BandAdapter().load_bands()
        return self.run_detection(red, nir, swir)

    def _validate_bands(self, red_band: BandGrid, nir_band: BandGrid, swir_band: BandGrid) -> None:
        if not red_band or not red_band[0]:
            raise ValueError("Band grids must not be empty")
        row_count = len(red_band)
        col_count = len(red_band[0])
        for name, band in {"red": red_band, "nir": nir_band, "swir": swir_band}.items():
            if len(band) != row_count:
                raise ValueError(f"{name} band row count does not match")
            if any(len(row) != col_count for row in band):
                raise ValueError(f"{name} band grid must be rectangular and match other bands")

    def _density_level(self, coverage_ratio: float) -> str:
        if coverage_ratio >= 0.35:
            return "very_high"
        if coverage_ratio >= 0.18:
            return "high"
        if coverage_ratio >= 0.06:
            return "medium"
        if coverage_ratio > 0:
            return "low"
        return "none"
