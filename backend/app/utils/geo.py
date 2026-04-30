import math


EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def destination_point(lat: float, lon: float, bearing_degrees: float, distance_nm: float) -> tuple[float, float]:
    bearing = math.radians(bearing_degrees)
    angular_distance = distance_nm / EARTH_RADIUS_NM
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)
    phi2 = math.asin(
        math.sin(phi1) * math.cos(angular_distance)
        + math.cos(phi1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(phi1),
        math.cos(angular_distance) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), ((math.degrees(lambda2) + 540) % 360) - 180


def bbox_polygon(lat: float, lon: float, radius_nm: float) -> dict:
    north, _ = destination_point(lat, lon, 0, radius_nm)
    south, _ = destination_point(lat, lon, 180, radius_nm)
    _, east = destination_point(lat, lon, 90, radius_nm)
    _, west = destination_point(lat, lon, 270, radius_nm)
    return {
        "type": "Polygon",
        "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    }


def linestring(points: list[tuple[float, float]]) -> dict:
    return {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in points]}
