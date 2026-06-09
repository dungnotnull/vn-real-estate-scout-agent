"""Flood zone checking using MONRE data and OpenStreetMap layers."""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FloodRisk(Enum):
    """Flood risk levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


@dataclass
class FloodZoneInfo:
    """Flood zone information for a location."""
    latitude: float
    longitude: float
    flood_risk: FloodRisk
    flood_zone_id: Optional[str] = None
    historical_flood_count: int = 0
    last_flood_year: Optional[int] = None
    data_source: str = "MONRE"  # MONRE, OSM, WorldBank
    confidence: float = 0.0  # 0-1 confidence in risk assessment

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'flood_risk': self.flood_risk.value,
            'flood_zone_id': self.flood_zone_id,
            'historical_flood_count': self.historical_flood_count,
            'last_flood_year': self.last_flood_year,
            'data_source': self.data_source,
            'confidence': self.confidence
        }


class FloodZoneChecker:
    """Flood zone checker using MONRE and OpenStreetMap data."""

    # Approximate flood-prone areas in major cities (simplified)
    # In production, load from actual shapefiles
    KNOWN_FLOOD_ZONES = {
        'Ho Chi Minh City': {
            'HIGH': [
                # Binh Thanh District - low-lying areas
                {'lat_range': (10.78, 10.82), 'lon_range': (106.68, 106.72)},
                # District 2 - Thu Thiem area
                {'lat_range': (10.78, 10.82), 'lon_range': (106.72, 106.78)},
                # District 7 - partially flood-prone
                {'lat_range': (10.73, 10.78), 'lon_range': (106.65, 106.72)},
            ],
            'MEDIUM': [
                # District 8 - near canals
                {'lat_range': (10.72, 10.77), 'lon_range': (106.63, 106.69)},
                # Nha Be district
                {'lat_range': (10.68, 10.73), 'lon_range': (106.70, 106.78)},
            ]
        },
        'Hanoi': {
            'HIGH': [
                # Red River banks
                {'lat_range': (20.98, 21.05), 'lon_range': (105.80, 105.95)},
                # West Lake area (heavy rain flooding)
                {'lat_range': (21.03, 21.08), 'lon_range': (105.80, 105.85)},
            ],
            'MEDIUM': [
                # Hoang Mai district
                {'lat_range': (20.95, 21.00), 'lon_range': (105.85, 105.95)},
            ]
        }
    }

    def __init__(self, shapefile_path: Optional[str] = None):
        """Initialize flood zone checker.

        Args:
            shapefile_path: Path to MONRE flood shapefile (optional)
        """
        self.shapefile_path = shapefile_path
        self.flood_data = None
        self.gdf = None

    def load_flood_data(self, city: str = "Ho Chi Minh City") -> bool:
        """Load flood zone shapefile for a city.

        Args:
            city: City name

        Returns:
            True if loaded successfully, False otherwise
        """
        # Placeholder implementation
        # In production:
        # import geopandas as gpd
        #
        # if self.shapefile_path:
        #     try:
        #         self.gdf = gpd.read_file(self.shapefile_path)
        #         self.flood_data = self.gdf
        #         logger.info(f"Loaded flood data from {self.shapefile_path}")
        #         return True
        #     except Exception as e:
        #         logger.error(f"Failed to load shapefile: {e}")
        #
        # # Fall back to hardcoded zones
        # logger.info(f"Using hardcoded flood zones for {city}")
        # return True

        return True

    def check_flood_risk(self, latitude: float, longitude: float, city: str = "Ho Chi Minh City") -> FloodZoneInfo:
        """Check flood risk for a specific location.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            city: City name

        Returns:
            FloodZoneInfo with risk assessment
        """
        # Check against known flood zones
        city_zones = self.KNOWN_FLOOD_ZONES.get(city, {})

        # Check HIGH risk zones first
        for zone in city_zones.get('HIGH', []):
            if self._point_in_zone(latitude, longitude, zone):
                return FloodZoneInfo(
                    latitude=latitude,
                    longitude=longitude,
                    flood_risk=FloodRisk.HIGH,
                    data_source="KNOWN_ZONES",
                    confidence=0.7
                )

        # Check MEDIUM risk zones
        for zone in city_zones.get('MEDIUM', []):
            if self._point_in_zone(latitude, longitude, zone):
                return FloodZoneInfo(
                    latitude=latitude,
                    longitude=longitude,
                    flood_risk=FloodRisk.MEDIUM,
                    data_source="KNOWN_ZONES",
                    confidence=0.6
                )

        # If not in known zones, assume LOW risk
        return FloodZoneInfo(
            latitude=latitude,
            longitude=longitude,
            flood_risk=FloodRisk.LOW,
            data_source="KNOWN_ZONES",
            confidence=0.5
        )

    def _point_in_zone(self, lat: float, lon: float, zone: Dict[str, Tuple[float, float]]) -> bool:
        """Check if point is in a rectangular zone.

        Args:
            lat: Point latitude
            lon: Point longitude
            zone: Zone definition with lat_range and lon_range

        Returns:
            True if point is in zone
        """
        lat_min, lat_max = zone['lat_range']
        lon_min, lon_max = zone['lon_range']
        return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

    def calculate_flood_score(self, flood_info: FloodZoneInfo) -> float:
        """Calculate flood score for ranking (0-1, higher is better).

        Args:
            flood_info: Flood zone information

        Returns:
            Score 0-1
        """
        risk_scores = {
            FloodRisk.LOW: 1.0,
            FloodRisk.MEDIUM: 0.5,
            FloodRisk.HIGH: 0.0,
            FloodRisk.UNKNOWN: 0.3  # Penalty for unknown
        }
        return risk_scores.get(flood_info.flood_risk, 0.3) * flood_info.confidence

    def batch_check_flood_risk(self, locations: List[Tuple[float, float]], city: str = "Ho Chi Minh City") -> List[FloodZoneInfo]:
        """Check flood risk for multiple locations.

        Args:
            locations: List of (lat, lon) points
            city: City name

        Returns:
            List of FloodZoneInfo
        """
        return [self.check_flood_risk(lat, lon, city) for lat, lon in locations]

    def __enter__(self):
        """Context manager entry."""
        self.load_flood_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
