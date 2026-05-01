from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.models.domain import CollectionZone, SargassumObservation
from app.services.drift_prediction_service import DriftInputs, DriftPredictionService
from app.services.patch_service import PatchService
from app.utils.geo import haversine_nm

RED_WAVELENGTH_NM = 665.0
NIR_WAVELENGTH_NM = 842.0
SWIR_WAVELENGTH_NM = 1610.0

BandGrid = list[list[float]]
MaskGrid = list[list[bool]]


@dataclass(frozen=True)
class SpectralMasks:
    cloud_mask: MaskGrid | None = None
    land_mask: MaskGrid | None = None
    sun_glint_mask: MaskGrid | None = None


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


class SpectralMaskProvider(Protocol):
    def load_masks(self) -> SpectralMasks:
        """Return optional exclusion masks aligned to the Sentinel-2 band grids."""


class NoOpSpectralMaskProvider:
    def load_masks(self) -> SpectralMasks:
        return SpectralMasks()


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
        masks: SpectralMasks | None = None,
    ) -> tuple[MaskGrid, list[SpectralPixel]]:
        thresholds = thresholds or SpectralDetectionThresholds()
        self._validate_bands(red_band, nir_band, swir_band)
        masks = masks or SpectralMasks()
        self._validate_masks(masks, len(red_band), len(red_band[0]))
        mask: MaskGrid = []
        pixels: list[SpectralPixel] = []
        for row_index, red_row in enumerate(red_band):
            mask_row: list[bool] = []
            for col_index, red in enumerate(red_row):
                nir = nir_band[row_index][col_index]
                swir = swir_band[row_index][col_index]
                ndvi = self.calculate_ndvi(red, nir)
                fai = self.calculate_fai(red, nir, swir)
                excluded = self._is_masked(row_index, col_index, masks)
                detected = (
                    not excluded
                    and fai >= thresholds.min_fai
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
                        "source_type": "spectral_detection",
                    },
                }
            )
        return features

    def cluster_adjacent_pixels(self, pixels: list[SpectralPixel]) -> list[list[SpectralPixel]]:
        by_cell = {(pixel.row, pixel.col): pixel for pixel in pixels}
        visited: set[tuple[int, int]] = set()
        clusters: list[list[SpectralPixel]] = []
        for cell, pixel in by_cell.items():
            if cell in visited:
                continue
            stack = [cell]
            visited.add(cell)
            cluster: list[SpectralPixel] = []
            while stack:
                current = stack.pop()
                cluster.append(by_cell[current])
                row, col = current
                for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                    if neighbor in by_cell and neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            clusters.append(sorted(cluster, key=lambda item: (item.row, item.col)))
        return clusters

    def detections_to_polygon_features(
        self, pixels: list[SpectralPixel], grid: RasterGridDefinition | None = None
    ) -> list[dict]:
        grid = grid or RasterGridDefinition()
        features: list[dict] = []
        for cluster_index, cluster in enumerate(self.cluster_adjacent_pixels(pixels), start=1):
            if len(cluster) < 2:
                continue
            rows = [pixel.row for pixel in cluster]
            cols = [pixel.col for pixel in cluster]
            north = grid.origin_latitude - (min(rows) - 0.5) * grid.pixel_size_degrees
            south = grid.origin_latitude - (max(rows) + 0.5) * grid.pixel_size_degrees
            west = grid.origin_longitude + (min(cols) - 0.5) * grid.pixel_size_degrees
            east = grid.origin_longitude + (max(cols) + 0.5) * grid.pixel_size_degrees
            mean_ndvi = sum(pixel.ndvi for pixel in cluster) / len(cluster)
            mean_fai = sum(pixel.fai for pixel in cluster) / len(cluster)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [round(west, 6), round(south, 6)],
                                [round(east, 6), round(south, 6)],
                                [round(east, 6), round(north, 6)],
                                [round(west, 6), round(north, 6)],
                                [round(west, 6), round(south, 6)],
                            ]
                        ],
                    },
                    "properties": {
                        "cluster_id": cluster_index,
                        "pixel_count": len(cluster),
                        "mean_ndvi": round(mean_ndvi, 4),
                        "mean_fai": round(mean_fai, 5),
                        "source_type": "spectral_detection",
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
                    source_type="spectral_detection",
                    source_reference=f"{source_reference}:r{pixel.row}:c{pixel.col}",
                    density_level=summary["density_level"],
                    estimated_area_m2=100.0,
                    confidence_score=summary["confidence_score"],
                    notes=f"Sentinel-2-compatible spectral candidate NDVI={pixel.ndvi}, FAI={pixel.fai}",
                )
            )
        return observations

    def ingest_detection_result(
        self,
        db: Session,
        detection_result: dict[str, Any],
        source_reference: str = "sentinel2_manual_scene",
        min_confidence: float = 0.65,
        duplicate_distance_nm: float = 0.1,
        duplicate_window_hours: int = 24,
        create_patch: bool = True,
        run_drift_prediction: bool = False,
        drift_horizon_hours: int = 72,
    ) -> dict[str, Any]:
        """Persist confirmed spectral candidates as observations and optionally a patch.

        This is intentionally explicit and threshold-gated so demo detections never
        become operational records unless an operator calls the ingest endpoint.
        """
        summary = detection_result.get("summary") or {}
        confidence = float(summary.get("confidence_score") or 0.0)
        features = detection_result.get("features") or []
        if confidence < min_confidence:
            return {
                "persisted": False,
                "reason": "confidence_below_threshold",
                "minimum_confidence": min_confidence,
                "summary": summary,
                "features": features,
                "polygon_features": detection_result.get("polygon_features") or [],
                "generated_polygons": len(detection_result.get("polygon_features") or []),
                "created_observation_ids": [],
                "created_patch_id": None,
                "created_patch_ids": [],
                "created_patch_reference": None,
                "created_patch_references": [],
                "created_observations": 0,
                "created_patches": 0,
                "created_collection_zone_id": None,
                "created_collection_zone_ids": [],
                "created_collection_zones": 0,
                "created_prediction_run_ids": [],
                "created_drift_zone_ids": [],
                "skipped_duplicates": 0,
                "drift_predictions": [],
            }

        observed_at = datetime.now(UTC)
        candidate_observations = self._features_to_observations(features, summary, source_reference, observed_at)
        created_observations: list[SargassumObservation] = []
        skipped_duplicates = 0

        for observation in candidate_observations:
            if self._has_recent_nearby_observation(
                db, observation, duplicate_distance_nm=duplicate_distance_nm, duplicate_window_hours=duplicate_window_hours
            ):
                skipped_duplicates += 1
                continue
            db.add(observation)
            created_observations.append(observation)

        if created_observations:
            db.flush()

        patch = None
        collection_zone = None
        prediction_run_ids: list[int] = []
        drift_zone_ids: list[int] = []
        drift_predictions = []
        if create_patch and created_observations:
            patch = PatchService().create_patch_from_observations(created_observations)
            patch.patch_reference = f"SPEC-{observed_at.strftime('%Y%m%d%H%M%S%f')}"
            patch.source_type = "spectral_detection"
            patch.source_reference = source_reference
            patch.confidence_score = confidence
            patch.density_level = summary.get("density_level") or patch.density_level
            patch.notes = (
                f"Generated from {len(created_observations)} Sentinel-2-compatible spectral detections; "
                f"mean NDVI={summary.get('mean_ndvi')}, mean FAI={summary.get('mean_fai')}."
            )
            db.add(patch)
            db.flush()

            collection_zone = self._collection_zone_from_patch(patch, source_reference)
            db.add(collection_zone)

            if run_drift_prediction:
                inputs = DriftInputs(horizon_hours=drift_horizon_hours)
                drift_service = DriftPredictionService()
                drift_result = drift_service.run_prediction_for_patch(patch, inputs)
                prediction_run, drift_zone = drift_service.persist_prediction_zone(
                    db,
                    patch,
                    inputs,
                    drift_result,
                    source_type="spectral_detection",
                    notes=f"Auto-persisted from spectral ingest {source_reference}.",
                )
                drift_predictions.append(drift_result)
                prediction_run_ids.append(prediction_run.id)
                if drift_zone is not None:
                    drift_zone_ids.append(drift_zone.id)

        db.commit()
        for observation in created_observations:
            db.refresh(observation)
        if patch is not None:
            db.refresh(patch)
        if collection_zone is not None:
            db.refresh(collection_zone)

        return {
            "persisted": bool(created_observations),
            "reason": "created" if created_observations else "all_candidates_duplicate_or_empty",
            "minimum_confidence": min_confidence,
            "source_type": "spectral_detection",
            "source_reference": source_reference,
            "summary": summary,
            "features": features,
            "polygon_features": detection_result.get("polygon_features") or [],
            "generated_polygons": len(detection_result.get("polygon_features") or []),
            "created_observation_ids": [observation.id for observation in created_observations],
            "created_patch_id": patch.id if patch else None,
            "created_patch_ids": [patch.id] if patch else [],
            "created_patch_reference": patch.patch_reference if patch else None,
            "created_patch_references": [patch.patch_reference] if patch else [],
            "created_observations": len(created_observations),
            "created_patches": 1 if patch else 0,
            "created_collection_zone_id": collection_zone.id if collection_zone else None,
            "created_collection_zone_ids": [collection_zone.id] if collection_zone else [],
            "created_collection_zones": 1 if collection_zone else 0,
            "created_prediction_run_ids": prediction_run_ids,
            "created_drift_zone_ids": drift_zone_ids,
            "skipped_duplicates": skipped_duplicates,
            "drift_predictions": drift_predictions,
            "duplicate_window_hours": duplicate_window_hours,
            "duplicate_distance_nm": duplicate_distance_nm,
        }

    def _collection_zone_from_patch(self, patch, source_reference: str) -> CollectionZone:
        severity_value = patch.severity.value if hasattr(patch.severity, "value") else str(patch.severity)
        severity_base = {"low": 35, "medium": 55, "high": 78, "critical": 92}.get(severity_value, 55)
        density_factor = {"low": 0.03, "medium": 0.06, "high": 0.09, "very_high": 0.12}.get(patch.density_level, 0.06)
        estimated_volume_kg = max(100.0, patch.estimated_area_m2 * density_factor)
        priority_score = min(100.0, severity_base + patch.confidence_score * 12)
        return CollectionZone(
            zone_name=f"Spectral Collection {patch.patch_reference}",
            center_latitude=patch.centroid_latitude,
            center_longitude=patch.centroid_longitude,
            severity=patch.severity,
            estimated_volume_kg=round(estimated_volume_kg, 2),
            priority_score=round(priority_score, 1),
            confidence_score=patch.confidence_score,
            source_type="spectral_detection",
            source_reference=source_reference,
            notes=f"Auto-created from confirmed spectral patch {patch.patch_reference}; available for vessel routing.",
        )

    def _features_to_observations(
        self, features: list[dict], summary: dict, source_reference: str, observed_at: datetime
    ) -> list[SargassumObservation]:
        observations: list[SargassumObservation] = []
        for feature in features:
            geometry = feature.get("geometry") or {}
            properties = feature.get("properties") or {}
            if geometry.get("type") != "Point":
                continue
            coordinates = geometry.get("coordinates") or []
            if len(coordinates) < 2:
                continue
            longitude, latitude = coordinates[0], coordinates[1]
            row = properties.get("row", "x")
            col = properties.get("col", "x")
            observations.append(
                SargassumObservation(
                    latitude=float(latitude),
                    longitude=float(longitude),
                    observed_at=observed_at,
                    source_type="spectral_detection",
                    source_reference=f"{source_reference}:r{row}:c{col}",
                    density_level=summary.get("density_level") or "medium",
                    estimated_area_m2=100.0,
                    confidence_score=float(summary.get("confidence_score") or 0.0),
                    notes=(
                        "Sentinel-2-compatible spectral candidate "
                        f"NDVI={properties.get('ndvi')}, FAI={properties.get('fai')}"
                    ),
                )
            )
        return observations

    def _has_recent_nearby_observation(
        self,
        db: Session,
        observation: SargassumObservation,
        duplicate_distance_nm: float,
        duplicate_window_hours: int,
    ) -> bool:
        window_start = observation.observed_at - timedelta(hours=duplicate_window_hours)
        recent = (
            db.query(SargassumObservation)
            .filter(SargassumObservation.observed_at >= window_start)
            .filter(SargassumObservation.source_type == "spectral_detection")
            .all()
        )
        for existing in recent:
            distance = haversine_nm(observation.latitude, observation.longitude, existing.latitude, existing.longitude)
            if distance <= duplicate_distance_nm:
                return True
        return False

    def run_detection(
        self,
        red_band: BandGrid,
        nir_band: BandGrid,
        swir_band: BandGrid,
        grid: RasterGridDefinition | None = None,
        thresholds: SpectralDetectionThresholds | None = None,
        masks: SpectralMasks | None = None,
    ) -> dict:
        grid = grid or RasterGridDefinition()
        masks = masks or SpectralMasks()
        mask, pixels = self.detect_likely_sargassum_pixels(red_band, nir_band, swir_band, thresholds, masks)
        georeferenced = self.georeference_pixels(pixels, grid)
        total_pixels = len(red_band) * len(red_band[0]) if red_band else 0
        summary = self.summarise_detection_confidence(georeferenced, total_pixels)
        polygon_features = self.detections_to_polygon_features(georeferenced, grid)
        summary["generated_polygons"] = len(polygon_features)
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
            "polygon_features": polygon_features,
            "masking": self.masking_summary(masks),
        }

    def run_mock_detection(self) -> dict:
        red, nir, swir = MockSentinel2BandAdapter().load_bands()
        return self.run_detection(red, nir, swir)

    def masks_from_payload(self, payload: dict[str, Any]) -> SpectralMasks:
        return SpectralMasks(
            cloud_mask=payload.get("cloud_mask"),
            land_mask=payload.get("land_mask"),
            sun_glint_mask=payload.get("sun_glint_mask"),
        )

    def masking_summary(self, masks: SpectralMasks) -> dict[str, Any]:
        return {
            "cloud_mask_applied": masks.cloud_mask is not None,
            "land_mask_applied": masks.land_mask is not None,
            "sun_glint_mask_applied": masks.sun_glint_mask is not None,
            "notes": "Mask hooks are local placeholders; future adapters can supply Sentinel cloud, shoreline, and sun-glint masks.",
        }

    def _is_masked(self, row: int, col: int, masks: SpectralMasks) -> bool:
        return any(
            mask is not None and bool(mask[row][col])
            for mask in (masks.cloud_mask, masks.land_mask, masks.sun_glint_mask)
        )

    def _validate_masks(self, masks: SpectralMasks, row_count: int, col_count: int) -> None:
        for name, mask in {
            "cloud_mask": masks.cloud_mask,
            "land_mask": masks.land_mask,
            "sun_glint_mask": masks.sun_glint_mask,
        }.items():
            if mask is None:
                continue
            if len(mask) != row_count or any(len(row) != col_count for row in mask):
                raise ValueError(f"{name} must be rectangular and match band dimensions")

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
