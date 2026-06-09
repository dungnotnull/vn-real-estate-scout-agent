"""Neo4j database client for vn-real-estate-scout."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from neo4j import GraphDatabase, Result
from src.config import neo4j
from src.db.neo4j_schema import (
    NEO4J_SCHEMA_INIT,
    CYPHER_TEMPLATES,
    PropertyNode,
    ListingNode,
    BrokerNode,
    PlatformNode,
    LocationNode,
)

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j client wrapper for property graph operations."""

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """Initialize Neo4j client.

        Args:
            uri: Neo4j bolt URI. Defaults to config.neo4j.uri
            user: Neo4j username. Defaults to config.neo4j.user
            password: Neo4j password. Defaults to config.neo4j.password
        """
        self.uri = uri or neo4j.uri
        self.user = user or neo4j.user
        self.password = password or neo4j.password
        self.driver: Optional[GraphDatabase.driver] = None

    def connect(self) -> bool:
        """Establish connection to Neo4j.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def initialize_schema(self) -> bool:
        """Initialize database schema with constraints and indexes.

        Returns:
            True if successful, False otherwise.
        """
        if not self.driver:
            logger.error("Not connected to Neo4j")
            return False

        try:
            with self.driver.session() as session:
                # Split and execute each constraint
                statements = NEO4J_SCHEMA_INIT.split('\n')
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt:
                        session.run(stmt)
                logger.info("Neo4j schema initialized")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return False

    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            logger.error("Not connected to Neo4j")
            return []

        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def create_property_node(self, property_data: Dict[str, Any]) -> Optional[str]:
        """Create a Property node.

        Args:
            property_data: Property attributes

        Returns:
            Property ID if created, None otherwise
        """
        property_id = property_data.get('id')
        if not property_id:
            logger.error("Property ID is required")
            return None

        result = self.execute_query(
            CYPHER_TEMPLATES['create_property'],
            {'property_id': property_id, 'property_data': property_data}
        )

        return property_id if result else None

    def create_listing_node(self, listing_data: Dict[str, Any]) -> Optional[str]:
        """Create a Listing node.

        Args:
            listing_data: Listing attributes

        Returns:
            Listing ID if created, None otherwise
        """
        listing_id = listing_data.get('id')
        if not listing_id:
            logger.error("Listing ID is required")
            return None

        result = self.execute_query(
            CYPHER_TEMPLATES['create_listing'],
            {'listing_data': listing_data}
        )

        return listing_id if result else None

    def create_or_update_broker(self, broker_data: Dict[str, Any]) -> Optional[str]:
        """Create or update a Broker node.

        Args:
            broker_data: Broker attributes

        Returns:
            Broker phone if created/updated, None otherwise
        """
        phone = broker_data.get('phone')
        if not phone:
            logger.error("Broker phone is required")
            return None

        result = self.execute_query(
            CYPHER_TEMPLATES['create_broker'],
            {'phone': phone, 'broker_data': broker_data}
        )

        return phone if result else None

    def create_platform_node(self, platform_data: Dict[str, Any]) -> Optional[str]:
        """Create a Platform node.

        Args:
            platform_data: Platform attributes

        Returns:
            Platform name if created, None otherwise
        """
        name = platform_data.get('name')
        if not name:
            logger.error("Platform name is required")
            return None

        result = self.execute_query(
            CYPHER_TEMPLATES['create_platform'],
            {'name': name, 'platform_data': platform_data}
        )

        return name if result else None

    def create_location_node(self, location_data: Dict[str, Any]) -> Optional[tuple]:
        """Create a Location node.

        Args:
            location_data: Location attributes

        Returns:
            (latitude, longitude) tuple if created, None otherwise
        """
        lat = location_data.get('latitude')
        lon = location_data.get('longitude')
        if lat is None or lon is None:
            logger.error("Location coordinates are required")
            return None

        result = self.execute_query(
            CYPHER_TEMPLATES['create_location'],
            {'latitude': lat, 'longitude': lon, 'location_data': location_data}
        )

        return (lat, lon) if result else None

    def link_listing_to_property(self, listing_id: str, property_id: str) -> bool:
        """Create LISTED_FOR relationship between listing and property.

        Args:
            listing_id: Listing ID
            property_id: Property ID

        Returns:
            True if successful, False otherwise
        """
        result = self.execute_query(
            CYPHER_TEMPLATES['link_listing_to_property'],
            {'listing_id': listing_id, 'property_id': property_id}
        )
        return len(result) > 0

    def link_listing_to_broker(self, listing_id: str, broker_phone: str) -> bool:
        """Create LISTED_BY relationship between listing and broker.

        Args:
            listing_id: Listing ID
            broker_phone: Broker phone number

        Returns:
            True if successful, False otherwise
        """
        result = self.execute_query(
            CYPHER_TEMPLATES['link_listing_to_broker'],
            {'listing_id': listing_id, 'broker_phone': broker_phone}
        )
        return len(result) > 0

    def link_listing_to_platform(self, listing_id: str, platform_name: str) -> bool:
        """Create POSTED_ON relationship between listing and platform.

        Args:
            listing_id: Listing ID
            platform_name: Platform name

        Returns:
            True if successful, False otherwise
        """
        result = self.execute_query(
            CYPHER_TEMPLATES['link_listing_to_platform'],
            {'listing_id': listing_id, 'platform_name': platform_name}
        )
        return len(result) > 0

    def link_property_to_location(self, property_id: str, latitude: float, longitude: float) -> bool:
        """Create LOCATED_AT relationship between property and location.

        Args:
            property_id: Property ID
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            True if successful, False otherwise
        """
        result = self.execute_query(
            CYPHER_TEMPLATES['link_property_to_location'],
            {'property_id': property_id, 'latitude': latitude, 'longitude': longitude}
        )
        return len(result) > 0

    def find_spatial_duplicates(self, radius_meters: float = 50.0, area_variance: float = 0.05) -> List[Dict[str, Any]]:
        """Find potential duplicate properties based on spatial proximity and area.

        Args:
            radius_meters: Maximum distance for duplicate detection
            area_variance: Maximum area variance ratio (default 5%)

        Returns:
            List of duplicate property pairs with metadata
        """
        query = f"""
        MATCH (p1:Property)-[:LOCATED_AT]->(loc1:Location)
        MATCH (p2:Property)-[:LOCATED_AT]->(loc2:Location)
        WHERE p1.id < p2.id
        WITH p1, p2,
             point.distance({{longitude: loc1.longitude, latitude: loc1.latitude}},
                           {{longitude: loc2.longitude, latitude: loc2.latitude}}) AS distance
        WHERE distance < {radius_meters}
        WITH p1, p2, distance,
             abs(p1.area_m2 - p2.area_m2) AS area_diff
        WHERE area_diff < (p1.area_m2 * {area_variance})
        RETURN p1, p2, distance, area_diff
        ORDER BY distance, area_diff
        """
        return self.execute_query(query)

    def find_listings_in_radius(self, latitude: float, longitude: float, radius_meters: float) -> List[Dict[str, Any]]:
        """Find all listings within a radius of a point.

        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_meters: Search radius in meters

        Returns:
            List of properties and listings within radius
        """
        return self.execute_query(
            CYPHER_TEMPLATES['find_listings_in_radius'],
            {'latitude': latitude, 'longitude': longitude, 'radius_meters': radius_meters}
        )

    def get_broker_reputation(self) -> List[Dict[str, Any]]:
        """Get all brokers with reputation scores.

        Returns:
            List of brokers with reputation data
        """
        return self.execute_query(CYPHER_TEMPLATES['find_broker_reputation'])

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
