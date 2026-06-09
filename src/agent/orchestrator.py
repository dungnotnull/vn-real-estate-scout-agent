"""Main agent orchestrator coordinating all modules."""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Current state of the agent processing loop."""
    phase: str = "initialized"
    listings_processed: int = 0
    duplicates_found: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    """Final result from agent processing."""
    user_id: str
    total_listings_found: int
    genuine_listings_count: int
    top_candidates: List[Dict[str, Any]]
    processing_time_seconds: float
    state: AgentState
    report_path: Optional[str] = None


class RealEstateAgent:
    """Main agent orchestrator for vn-real-estate-scout."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent."""
        self.config = config or {}
        self.state = AgentState()

        # Initialize modules
        self.neo4j_client = None
        self.chroma_store = None
        self.ranker = None
        self.ner_model = None
        self.embedder = None
        self.classifier = None
        self.reputation_scorer = None
        self.geocoder = None
        self.flood_checker = None
        self.distance_client = None
        self.isochrone_client = None
        self.summarizer = None
        self.llm_client = None

    async def search_and_rank(
        self,
        user_preferences: Dict[str, Any],
        user_id: Optional[str] = None,
        max_listings: int = 1000
    ) -> AgentResult:
        """Main agent loop: search, process, and rank properties."""
        start_time = datetime.now()
        self.state = AgentState(phase="scraping")

        try:
            # Phase 1: Scraping
            logger.info("Starting scraping phase")
            raw_listings = await self._scrape_listings(user_preferences, max_listings)
            self.state.listings_processed = len(raw_listings)

            if not raw_listings:
                logger.warning("No listings found during scraping")
                return self._empty_result(user_id, start_time)

            # Phase 2: NLP extraction
            self.state.phase = "ner"
            logger.info("Starting NER extraction")
            enriched_listings = await self._extract_entities(raw_listings)

            # Phase 3: Deduplication
            self.state.phase = "deduplication"
            logger.info("Starting deduplication")
            genuine_listings = await self._deduplicate_listings(enriched_listings)
            self.state.duplicates_found = len(enriched_listings) - len(genuine_listings)

            # Phase 4: Geospatial analysis
            self.state.phase = "geospatial"
            logger.info("Starting geospatial analysis")
            geo_enriched = await self._analyze_geospatial(genuine_listings, user_preferences)

            # Phase 5: Scoring and ranking
            self.state.phase = "scoring"
            logger.info("Starting scoring and ranking")
            ranked = self._rank_properties(geo_enriched, user_preferences)

            # Phase 6: Report generation
            self.state.phase = "reporting"
            logger.info("Generating report")
            top_candidates = ranked[:5]

            processing_time = (datetime.now() - start_time).total_seconds()

            result = AgentResult(
                user_id=user_id or "anonymous",
                total_listings_found=len(raw_listings),
                genuine_listings_count=len(genuine_listings),
                top_candidates=[c.to_dict() if hasattr(c, 'to_dict') else c for c in top_candidates],
                processing_time_seconds=processing_time,
                state=self.state
            )

            logger.info(f"Agent completed: {len(raw_listings)} listings, {len(genuine_listings)} genuine")
            return result

        except Exception as e:
            logger.error(f"Agent processing failed: {e}", exc_info=True)
            self.state.phase = "error"
            self.state.errors.append(str(e))
            return self._empty_result(user_id, start_time)

    async def _scrape_listings(self, preferences: Dict[str, Any], max_listings: int) -> List[Dict[str, Any]]:
        """Scrape listings from all platforms."""
        from src.scrapers.batdongsan import BatdodsanScraper, ChototScraper

        all_listings = []
        scrapers = [BatdodsanScraper(), ChototScraper()]

        for scraper in scrapers:
            try:
                listings = await scraper.search_listings(
                    city=preferences.get('preferred_cities', ['Ho Chi Minh City'])[0] if preferences.get('preferred_cities') else 'Ho Chi Minh City',
                    property_type=preferences.get('property_types', ['apartment'])[0] if preferences.get('property_types') else 'apartment',
                    min_price=preferences.get('min_price'),
                    max_price=preferences.get('max_price'),
                    min_area=preferences.get('min_area'),
                    max_area=preferences.get('max_area'),
                    max_pages=3
                )

                for listing in listings:
                    all_listings.append(listing.to_dict())

                logger.info(f"Scraped {len(listings)} listings from {scraper.platform_name}")

            except Exception as e:
                logger.error(f"Scraper {scraper.platform_name} failed: {e}")
                continue

        return all_listings[:max_listings]

    async def _extract_entities(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract entities using NER."""
        from src.nlp.entities import PhoBERTNER

        if not self.ner_model:
            self.ner_model = PhoBERTNER(use_model=False)
            self.ner_model.load_model()

        enriched_listings = []

        for listing in listings:
            description = listing.get('description', '')
            title = listing.get('title', '')
            text = f"{title}. {description}" if title and description else (title or description)

            try:
                ner_result = self.ner_model.extract_entities(text)
                listing.update(ner_result.to_dict())
                enriched_listings.append(listing)
            except Exception as e:
                logger.debug(f"NER extraction failed: {e}")
                enriched_listings.append(listing)

        return enriched_listings

    async def _deduplicate_listings(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate listings."""
        # Initialize modules if needed
        if not self.neo4j_client:
            from src.db.neo4j_client import Neo4jClient
            self.neo4j_client = Neo4jClient()
            self.neo4j_client.connect()
            self.neo4j_client.initialize_schema()

        if not self.embedder:
            from src.ml.embeddings import EmbeddingGenerator
            self.embedder = EmbeddingGenerator()
            self.embedder.load_model()

        if not self.classifier:
            from src.ml.classifier import FakeListingClassifier
            self.classifier = FakeListingClassifier()

        # Generate embeddings
        texts = [f"{l.get('title', '')} {l.get('description', '')}" for l in listings]
        embeddings = self.embedder.encode(texts)

        # Find duplicates using embeddings
        genuine_listings = []
        duplicate_ids = set()

        for i, (listing, embedding) in enumerate(zip(listings, embeddings)):
            if listing.get('listing_id') in duplicate_ids:
                continue

            # Check for similar listings
            for j, other_listing in enumerate(listings[i+1:], i+1):
                other_embedding = embeddings[j]

                similarity = self.embedder.compute_similarity(embedding, other_embedding)

                if similarity > 0.95:  # High similarity threshold
                    duplicate_ids.add(other_listing.get('listing_id'))

            # Score authenticity
            try:
                features = self.classifier._extract_features(listing)
                features_array = [list(features.values())]
                prediction = self.classifier.predict(features_array)[0]

                if prediction != 2:  # Not confirmed duplicate
                    genuine_listings.append(listing)
            except Exception:
                genuine_listings.append(listing)

        return genuine_listings

    async def _analyze_geospatial(self, listings: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze geospatial features."""
        # Initialize geospatial modules if needed
        if not self.geocoder:
            from src.nlp.address_parser import VietnameseAddressParser
            self.geocoder = VietnameseAddressParser(use_model=False)
            self.geocoder.load_model()

        if not self.flood_checker:
            from src.geo.flood import FloodZoneChecker
            self.flood_checker = FloodZoneChecker()
            self.flood_checker.load_flood_data()

        if not self.distance_client:
            from src.geo.distance import GoogleMapsDistanceMatrix
            self.distance_client = GoogleMapsDistanceMatrix(api_key=self.config.get('google_maps_api_key'))
            self.distance_client.load_client()

        # Geocode and analyze each listing
        geo_enriched = []

        for listing in listings:
            try:
                # Geocode address
                address = listing.get('address_raw', '')
                if address:
                    parsed = self.geocoder.parse(address)
                    geocoded = self.geocoder.geocode(
                        parsed,
                        api_key=self.config.get('google_maps_api_key')
                    )

                    if geocoded.latitude and geocoded.longitude:
                        listing['latitude'] = geocoded.latitude
                        listing['longitude'] = geocoded.longitude

                # Check flood risk
                if listing.get('latitude') and listing.get('longitude'):
                    flood_info = self.flood_checker.check_flood_risk(
                        listing['latitude'],
                        listing['longitude'],
                        preferences.get('preferred_cities', ['Ho Chi Minh City'])[0] if preferences.get('preferred_cities') else 'Ho Chi Minh City'
                    )
                    listing['flood_info'] = flood_info.to_dict()

                geo_enriched.append(listing)

            except Exception as e:
                logger.debug(f"Geospatial analysis failed: {e}")
                geo_enriched.append(listing)

        return geo_enriched

    def _rank_properties(self, listings: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List:
        """Score and rank properties."""
        from src.scoring.ranker import PropertyRanker

        if not self.ranker:
            self.ranker = PropertyRanker()

        # Calculate commute scores if workplace provided
        commute_scores = {}
        if preferences.get('workplace_latitude') and preferences.get('workplace_longitude'):
            for listing in listings:
                if listing.get('latitude') and listing.get('longitude'):
                    try:
                        from src.geo.distance import GoogleMapsDistanceMatrix, DistanceResult

                        distance_result = DistanceResult(
                            origin_address=f"{preferences['workplace_latitude']},{preferences['workplace_longitude']}",
                            destination_address=f"{listing['latitude']},{listing['longitude']}",
                            distance_meters=0,
                            duration_seconds=0
                        )

                        commute_score = self.distance_client.calculate_commute_score(
                            distance_result,
                            max_acceptable_minutes=preferences.get('max_commute_minutes', 60)
                        )

                        commute_scores[listing.get('listing_id', '')] = commute_score.score
                    except Exception:
                        pass

        # Rank properties
        ranked = self.ranker.rank_properties(
            listings,
            preferences,
            commute_scores=commute_scores
        )

        return ranked

    def _empty_result(self, user_id: Optional[str], start_time: datetime) -> AgentResult:
        """Create empty result."""
        return AgentResult(
            user_id=user_id or "anonymous",
            total_listings_found=0,
            genuine_listings_count=0,
            top_candidates=[],
            processing_time_seconds=(datetime.now() - start_time).total_seconds(),
            state=self.state
        )


class AgentOrchestrator:
    """High-level orchestrator for agent lifecycle management."""

    def __init__(self):
        """Initialize orchestrator."""
        self.agent = None

    def create_agent(self, config: Optional[Dict[str, Any]] = None) -> RealEstateAgent:
        """Create a new agent instance."""
        self.agent = RealEstateAgent(config)
        return self.agent

    async def process_search_request(
        self,
        user_preferences: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> AgentResult:
        """Process a one-time search request."""
        if not self.agent:
            self.agent = self.create_agent()

        return await self.agent.search_and_rank(user_preferences, user_id)

    def start_background_monitoring(self, user_preferences: Dict[str, Any], interval_hours: int = 4):
        """Start continuous monitoring."""
        if not self.agent:
            self.agent = self.create_agent()

        from src.scheduler.scraper_scheduler import ScrapingManager
        scheduler = ScrapingManager()
        scheduler.start()

        logger.info(f"Started background monitoring with {interval_hours}h interval")
