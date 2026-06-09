"""Neo4j property graph schema for vn-real-estate-scout."""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

# Node Labels
NODE_LABELS = {
    "PROPERTY": "Property",
    "LISTING": "Listing",
    "BROKER": "Broker",
    "PLATFORM": "Platform",
    "LOCATION": "Location",
    "USER": "User",
    "SEARCH_SESSION": "SearchSession",
}

# Relationship Types
RELATIONSHIP_TYPES = {
    "LISTED_BY": "LISTED_BY",
    "LOCATED_AT": "LOCATED_AT",
    "SIMILAR_TO": "SIMILAR_TO",
    "SAME_AS": "SAME_AS",
    "POSTED_ON": "POSTED_ON",
    "SEARCHED_FOR": "SEARCHED_FOR",
    "HAS_PREFERENCE": "HAS_PREFERENCE",
    "RATED": "RATED",
}

# Schema definitions as Cypher queries
SCHEMA_CONSTRAINTS = [
    # Property node constraints
    f"CREATE CONSTRAINT property_id_unique IF NOT EXISTS FOR (p:{NODE_LABELS['PROPERTY']}) REQUIRE p.id IS UNIQUE",
    f"CREATE INDEX property_location IF NOT EXISTS FOR (p:{NODE_LABELS['PROPERTY']}) ON (p.latitude, p.longitude)",
    f"CREATE INDEX property_area IF NOT EXISTS FOR (p:{NODE_LABELS['PROPERTY']}) ON (p.area_m2)",

    # Listing node constraints
    f"CREATE CONSTRAINT listing_id_unique IF NOT EXISTS FOR (l:{NODE_LABELS['LISTING']}) REQUIRE l.id IS UNIQUE",
    f"CREATE INDEX listing_price IF NOT EXISTS FOR (l:{NODE_LABELS['LISTING']}) ON (l.price_vnd)",
    f"CREATE INDEX listing_date IF NOT EXISTS FOR (l:{NODE_LABELS['LISTING']}) ON (l.posted_date)",

    # Broker node constraints
    f"CREATE CONSTRAINT broker_phone_unique IF NOT EXISTS FOR (b:{NODE_LABELS['BROKER']}) REQUIRE b.phone IS UNIQUE",

    # Platform node constraints
    f"CREATE CONSTRAINT platform_name_unique IF NOT EXISTS FOR (pl:{NODE_LABELS['PLATFORM']}) REQUIRE pl.name IS UNIQUE",

    # Location node constraints
    f"CREATE CONSTRAINT location_coords_unique IF NOT EXISTS FOR (loc:{NODE_LABELS['LOCATION']}) REQUIRE (loc.latitude, loc.longitude) IS NODE KEY",
]

# Neo4j schema initialization
NEO4J_SCHEMA_INIT = "\n".join(SCHEMA_CONSTRAINTS)


@dataclass
class PropertyNode:
    """Property node schema."""
    id: str  # Generated hash of (address, area, type)
    address_raw: str
    address_normalized: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_m2: Optional[float] = None
    property_type: Optional[str] = None  # apartment, house, land, commercial
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    legal_status: Optional[str] = None  # SHR, SHTT, dat_tho_cu, etc.
    year_built: Optional[int] = None
    flood_risk: Optional[str] = None  # LOW, MEDIUM, HIGH
    created_at: datetime = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ListingNode:
    """Listing node schema."""
    id: str  # Platform-specific listing ID
    property_id: str  # Reference to Property node
    platform: str  # batdongsan, chotot, facebook, etc.
    url: str
    title: str
    description: str
    price_vnd: Optional[float] = None
    price_per_m2: Optional[float] = None
    listed_by: Optional[str] = None  # Broker name/phone
    contact_phone: Optional[str] = None
    posted_date: Optional[datetime] = None
    scraped_date: Optional[datetime] = None
    is_active: bool = True
    authenticity_score: Optional[float] = None  # 0-1, from XGBoost
    duplicate_cluster_id: Optional[str] = None
    image_urls: List[str] = None
    image_hash: Optional[str] = None
    amenities: List[str] = None
    created_at: datetime = None

    def to_dict(self) -> dict:
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                if isinstance(v, list) and v:
                    result[k] = v
                elif not isinstance(v, list):
                    result[k] = v
        return result


@dataclass
class BrokerNode:
    """Broker node schema."""
    phone: str  # Primary identifier
    name: Optional[str] = None
    platform: Optional[str] = None
    reputation_score: Optional[float] = None  # 0-1, aggregated from feedback
    total_listings: int = 0
    confirmed_fake_count: int = 0
    account_created: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    is_suspicious: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PlatformNode:
    """Platform node schema."""
    name: str  # batdongsan, chotot, facebook, alonhadat, etc.
    base_url: str
    listing_count: int = 0
    last_scraped: Optional[datetime] = None
    scraper_status: str = "active"  # active, blocked, deprecated

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class LocationNode:
    """Location node schema."""
    latitude: float
    longitude: float
    country: str = "Vietnam"
    city: Optional[str] = None  # Ho Chi Minh City, Hanoi, etc.
    district: Optional[str] = None  # Quan 1, Quan 7, etc.
    ward: Optional[str] = None  # Phu My Hung, etc.
    street: Optional[str] = None
    postal_code: Optional[str] = None
    flood_zone_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != ""}


@dataclass
class SimilarityEdge:
    """SIMILAR_TO relationship schema."""
    source_listing_id: str
    target_listing_id: str
    similarity_score: float  # 0-1 cosine similarity
    similarity_type: str  # semantic, spatial, visual
    created_at: datetime = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and k not in ["source_listing_id", "target_listing_id"]}


# Cypher query templates
CYPHER_TEMPLATES = {
    "create_property": """
        MERGE (p:Property {{id: $property_id}})
        SET p += $property_data
        RETURN p
    """,

    "create_listing": """
        CREATE (l:Listing)
        SET l += $listing_data
        RETURN l
    """,

    "create_broker": """
        MERGE (b:Broker {{phone: $phone}})
        SET b += $broker_data
        RETURN b
    """,

    "create_platform": """
        MERGE (pl:Platform {{name: $name}})
        SET pl += $platform_data
        RETURN pl
    """,

    "create_location": """
        MERGE (loc:Location {{latitude: $latitude, longitude: $longitude}})
        SET loc += $location_data
        RETURN loc
    """,

    "link_listing_to_property": """
        MATCH (l:Listing {{id: $listing_id}})
        MATCH (p:Property {{id: $property_id}})
        MERGE (l)-[:LISTED_FOR]->(p)
        RETURN l, p
    """,

    "link_listing_to_broker": """
        MATCH (l:Listing {{id: $listing_id}})
        MATCH (b:Broker {{phone: $broker_phone}})
        MERGE (l)-[:LISTED_BY]->(b)
        RETURN l, b
    """,

    "link_listing_to_platform": """
        MATCH (l:Listing {{id: $listing_id}})
        MATCH (pl:Platform {{name: $platform_name}})
        MERGE (l)-[:POSTED_ON]->(pl)
        RETURN l, pl
    """,

    "link_property_to_location": """
        MATCH (p:Property {{id: $property_id}})
        MATCH (loc:Location {{latitude: $latitude, longitude: $longitude}})
        MERGE (p)-[:LOCATED_AT]->(loc)
        RETURN p, loc
    """,

    "find_spatial_duplicates": """
        MATCH (p1:Property)-[:LOCATED_AT]->(loc1:Location)
        MATCH (p2:Property)-[:LOCATED_AT]->(loc2:Location)
        WHERE p1.id < p2.id
        WITH p1, p2,
             point.distance({{longitude: loc1.longitude, latitude: loc1.latitude}},
                           {{longitude: loc2.longitude, latitude: loc2.latitude}}) AS distance
        WHERE distance < 50  // 50 meters
        WITH p1, p2, distance,
             abs(p1.area_m2 - p2.area_m2) AS area_diff
        WHERE area_diff < (p1.area_m2 * 0.05)  // Within 5% area
        RETURN p1, p2, distance, area_diff
        ORDER BY distance, area_diff
    """,

    "find_broker_reputation": """
        MATCH (b:Broker)<-[:LISTED_BY]-(l:Listing)
        WITH b, count(l) AS total,
             sum(CASE WHEN l.authenticity_score < 0.5 THEN 1 ELSE 0 END) AS suspected_fakes
        WITH b, total, suspected_fakes,
             (1.0 - (suspected_fakes * 1.0 / total)) AS reputation
        WHERE total > 5
        RETURN b.phone, b.name, total, suspected_fakes, reputation
        ORDER BY reputation ASC
    """,

    "find_listings_in_radius": """
        MATCH (p:Property)-[:LOCATED_AT]->(loc:Location)
        WITH point({{longitude: $longitude, latitude: $latitude}}) AS center,
             point({{longitude: loc.longitude, latitude: loc.latitude}}) AS prop_point,
             p
        WHERE point.distance(center, prop_point) < $radius_meters
        RETURN DISTINCT p, loc
        ORDER BY point.distance(center, prop_point)
    """,
}
