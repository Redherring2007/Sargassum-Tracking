from datetime import UTC, datetime

from app.services.spectral_detection_service import MockSentinel2BandAdapter, SpectralDetectionService, SpectralMasks


def test_ndvi_and_fai_calculation():
    service = SpectralDetectionService()
    ndvi = service.calculate_ndvi(red=0.04, nir=0.08)
    fai = service.calculate_fai(red=0.04, nir=0.08, swir=0.05)

    assert round(ndvi, 3) == 0.333
    assert fai > 0


def test_safe_divide_handles_zero_denominator():
    service = SpectralDetectionService()
    assert service.safe_divide(1, 0) == 0
    assert service.safe_divide(1, 0, default=-1) == -1


def test_mock_detection_returns_geojson_features_and_summary():
    service = SpectralDetectionService()
    result = service.run_mock_detection()

    assert result["algorithm"] == "sentinel2_ndvi_fai_threshold"
    assert result["summary"]["detected_pixels"] > 0
    assert result["summary"]["confidence_score"] > 0
    assert result["features"]
    assert result["features"][0]["geometry"]["type"] == "Point"


def test_detection_mask_shape_matches_input_grid():
    service = SpectralDetectionService()
    red, nir, swir = MockSentinel2BandAdapter().load_bands()
    result = service.run_detection(red, nir, swir)

    assert len(result["mask"]) == len(red)
    assert len(result["mask"][0]) == len(red[0])


def test_spectral_features_use_persistence_source_type():
    service = SpectralDetectionService()
    result = service.run_mock_detection()

    assert result["features"][0]["properties"]["source_type"] == "spectral_detection"


def test_detection_to_observations_uses_spectral_source_type():
    service = SpectralDetectionService()
    result = service.run_mock_detection()
    observations = service._features_to_observations(
        result["features"], result["summary"], "unit_scene", observed_at=datetime.now(UTC)
    )

    assert observations
    assert observations[0].source_type == "spectral_detection"
    assert observations[0].source_reference.startswith("unit_scene:r")


def test_low_confidence_ingest_result_does_not_persist():
    service = SpectralDetectionService()
    result = service.run_mock_detection()
    response = service.ingest_detection_result(None, result, min_confidence=0.99)

    assert response["persisted"] is False
    assert response["reason"] == "confidence_below_threshold"
    assert response["created_observation_ids"] == []


class _EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _FakeDb:
    def __init__(self):
        self.added = []
        self._next_id = 1

    def query(self, *_args, **_kwargs):
        return _EmptyQuery()

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.flush()

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1


def test_ingest_detection_result_creates_observations_and_patch_when_confirmed():
    service = SpectralDetectionService()
    result = service.run_mock_detection()
    fake_db = _FakeDb()

    response = service.ingest_detection_result(fake_db, result, source_reference="unit_scene", min_confidence=0.5)

    assert response["persisted"] is True
    assert response["created_observations"] == result["summary"]["detected_pixels"]
    assert response["created_patch_id"] is not None
    assert response["source_type"] == "spectral_detection"


def test_detection_generates_polygon_features_for_adjacent_pixels():
    service = SpectralDetectionService()
    result = service.run_mock_detection()

    assert result["polygon_features"]
    assert result["polygon_features"][0]["geometry"]["type"] == "Polygon"
    assert result["summary"]["generated_polygons"] == len(result["polygon_features"])


def test_masks_exclude_detected_pixels():
    service = SpectralDetectionService()
    red, nir, swir = MockSentinel2BandAdapter().load_bands()
    no_mask = service.run_detection(red, nir, swir)
    cloud_mask = [[False for _ in row] for row in red]
    cloud_mask[1][1] = True
    masked = service.run_detection(red, nir, swir, masks=SpectralMasks(cloud_mask=cloud_mask))

    assert masked["summary"]["detected_pixels"] == no_mask["summary"]["detected_pixels"] - 1
    assert masked["masking"]["cloud_mask_applied"] is True


def test_ingest_detection_result_can_return_drift_prediction():
    service = SpectralDetectionService()
    result = service.run_mock_detection()
    fake_db = _FakeDb()

    response = service.ingest_detection_result(
        fake_db,
        result,
        source_reference="unit_scene_drift",
        min_confidence=0.5,
        run_drift_prediction=True,
        drift_horizon_hours=24,
    )

    assert response["created_patches"] == 1
    assert response["drift_predictions"]
    assert response["drift_predictions"][0]["future_positions"]
