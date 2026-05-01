from app.services.spectral_detection_service import MockSentinel2BandAdapter, SpectralDetectionService


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
