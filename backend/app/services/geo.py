from __future__ import annotations

import math


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками на Земле в метрах."""
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_within_radius(
    user_lat: float,
    user_lon: float,
    location_lat: float,
    location_lon: float,
    radius_meters: int,
) -> tuple[bool, float]:
    distance = haversine_meters(user_lat, user_lon, location_lat, location_lon)
    return distance <= radius_meters, distance
