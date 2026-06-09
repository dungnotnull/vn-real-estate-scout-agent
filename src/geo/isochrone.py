"""Mapbox Isochrone API for reachable zone analysis."""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IsochronePolygon:
    """Isochrone polygon representing reachable area."""
    center: Tuple[float, float]  # (latitude, longitude)
    minutes: int
    profile: str  # driving, walking, cycling
    coordinates: List[List[Tuple[float, float]]]  # Polygon exterior ring
    area_sqkm: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'center': self.center,
            'minutes': self.minutes,
            'profile': self.profile,
            'coordinates': self.coordinates,
            'area_sqkm': self.area_sqkm
        }


@dataclass
class PointInPolygonResult:
    """Result of point-in-polygon test."""
    point: Tuple[float, float]
    is_inside: bool
    distance_to_polygon_meters: Optional[float] = None


class MapboxIsochrone:
    """Mapbox Isochrone API client for reachable zone analysis."""

    API_BASE_URL = "https://api.mapbox.com/isochrone/v1"

    def __init__(self, access_token: Optional[str] = None):
        """Initialize Mapbox Isochrone client.

        Args:
            access_token: Mapbox public access token
        """
        self.access_token = access_token

    def get_isochrone(
        self,
        center: Tuple[float, float],
        minutes: int = 30,
        profile: str = "driving",
        contours_minutes: Optional[List[int]] = None
    ) -> Optional[IsochronePolygon]:
        """Get isochrone polygon for a given center and travel time.

        Args:
            center: (latitude, longitude) center point
            minutes: Travel time in minutes
            profile: Travel profile (driving, walking, cycling)
            contours_minutes: Optional list of contour minutes (e.g., [10, 20, 30])

        Returns:
            IsochronePolygon with coordinates
        """
        if not self.access_token:
            logger.warning("No Mapbox access token provided")
            return None

        # Placeholder implementation
        # In production:
        # import requests
        #
        # url = f"{self.API_BASE_URL}/{profile}/{center[1]},{center[0]}"
        # params = {
        #     'access_token': self.access_token,
        #     'contours_minutes': minutes if not contours_minutes else ','.join(map(str, contours_minutes)),
        #     'polygons': 'true',
        #     'denoise': '0.5'  # Remove small polygons
        # }
        #
        # response = requests.get(url, params=params)
        # if response.status_code == 200:
        #     data = response.json()
        #     # Parse polygon coordinates from GeoJSON
        #     coordinates = data['features'][0]['geometry']['coordinates']
        #     return IsochronePolygon(
        #         center=center,
        #         minutes=minutes,
        #         profile=profile,
        #         coordinates=coordinates[0] if coordinates else []
        #     )
        # else:
        #     logger.error(f"Isochrone request failed: {response.status_code}")
        #     return None

        return None

    def point_in_polygon(self, point: Tuple[float, float], polygon: IsochronePolygon) -> PointInPolygonResult:
        """Check if a point is inside the isochrone polygon.

        Args:
            point: (latitude, longitude) to test
            polygon: Isochrone polygon

        Returns:
            PointInPolygonResult with is_inside flag
        """
        # Placeholder implementation
        # In production, use shapely for point-in-polygon test:
        # from shapely.geometry import Point, Polygon
        #
        # shapely_point = Point(point[1], point[0])  # shapely uses (lon, lat)
        # shapely_poly = Polygon([(lon, lat) for lat, lon in polygon.coordinates[0]])
        #
        # is_inside = shapely_poly.contains(shapely_point)
        #
        # return PointInPolygonResult(
        #     point=point,
        #     is_inside=is_inside,
        #     distance_to_polygon_meters=shapely_point.distance(shapely_poly) * 111000  # Approx conversion
        # )

        return PointInPolygonResult(point=point, is_inside=False)

    def batch_check_locations(
        self,
        locations: List[Tuple[float, float]],
        polygon: IsochronePolygon
    ) -> List[PointInPolygonResult]:
        """Check multiple locations against polygon.

        Args:
            locations: List of (lat, lon) points
            polygon: Isochrone polygon

        Returns:
            List of PointInPolygonResult
        """
        return [self.point_in_polygon(loc, polygon) for loc in locations]

    def calculate_coverage_score(self, is_inside: bool, ideal_coverage: bool = True) -> float:
        """Calculate coverage score based on isochrone membership.

        Args:
            is_inside: Whether property is inside isochrone
            ideal_coverage: Whether being inside is desirable (True) or not

        Returns:
            Score 0-1
        """
        if ideal_coverage:
            return 1.0 if is_inside else 0.0
        else:
            return 0.0 if is_inside else 1.0

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
