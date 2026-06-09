"""Base scraper class and common utilities."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import random
from crawl4ai import AsyncWebCrawler
from src.config import scraper

logger = __import__('logging').getLogger(__name__)


@dataclass
class ScrapedListing:
    """Standardized listing data from any platform."""
    id: str  # Platform-specific ID
    platform: str
    url: str
    title: str
    description: str
    price_vnd: Optional[float] = None
    area_m2: Optional[float] = None
    property_type: Optional[str] = None  # apartment, house, land, commercial
    bedrooms: Optional[int] = None
    address_raw: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None
    posted_date: Optional[datetime] = None
    images: List[str] = None
    amenities: List[str] = None
    legal_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_verified: bool = False  # Platform verification badge
    source_html: Optional[str] = None  # Raw HTML for fallback parsing

    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.amenities is None:
            self.amenities = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    def __init__(self, platform_name: str):
        """Initialize base scraper.

        Args:
            platform_name: Platform identifier (batdongsan, chotot, facebook, etc.)
        """
        self.platform_name = platform_name
        self.rate_limit = scraper.rate_limit
        self.delay_min = scraper.delay_min
        self.delay_max = scraper.delay_max

    @abstractmethod
    async def search_listings(self, **search_params) -> List[ScrapedListing]:
        """Search for listings with given parameters.

        Args:
            **search_params: Platform-specific search parameters
                - city: str (e.g., "Ho Chi Minh City", "Hanoi")
                - district: str (e.g., "Quan 1", "Quan 7")
                - property_type: str (apartment, house, land)
                - min_price: float (VND)
                - max_price: float (VND)
                - min_area: float (m2)
                - max_area: float (m2)
                - listing_type: str (buy, rent)

        Returns:
            List of scraped listings
        """
        pass

    @abstractmethod
    async def get_listing_details(self, listing_id: str) -> Optional[ScrapedListing]:
        """Get detailed information for a specific listing.

        Args:
            listing_id: Platform-specific listing ID

        Returns:
            ScrapedListing with full details, or None if not found
        """
        pass

    async def _fetch_page(self, url: str, crawler: AsyncWebCrawler) -> Optional[str]:
        """Fetch a page with rate limiting and random delay.

        Args:
            url: URL to fetch
            crawler: AsyncWebCrawler instance

        Returns:
            Page content as string, or None if failed
        """
        # Apply random delay to avoid detection
        delay = random.uniform(self.delay_min, self.delay_max)
        await asyncio.sleep(delay)

        try:
            result = await crawler.arun(url=url)
            if result.success:
                return result.html
            else:
                logger.error(f"Failed to fetch {url}: {result.error_message}")
                return None
        except Exception as e:
            logger.error(f"Exception fetching {url}: {e}")
            return None

    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from URL.

        Args:
            url: Listing URL

        Returns:
            Extracted ID, or None if pattern doesn't match
        """
        # To be implemented by subclasses
        return None

    def _generate_listing_id(self, url: str) -> str:
        """Generate consistent ID from URL if extraction fails.

        Args:
            url: Listing URL

        Returns:
            Generated ID
        """
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]

    async def scrape_with_retry(self, url: str, max_retries: int = 3) -> Optional[ScrapedListing]:
        """Scrape a listing with retry logic.

        Args:
            url: Listing URL
            max_retries: Maximum number of retry attempts

        Returns:
            ScrapedListing if successful, None otherwise
        """
        listing_id = self._extract_listing_id(url) or self._generate_listing_id(url)

        for attempt in range(max_retries):
            try:
                async with AsyncWebCrawler() as crawler:
                    listing = await self.get_listing_details(listing_id)
                    if listing:
                        return listing
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")

        logger.error(f"All {max_retries} attempts failed for {url}")
        return None

    @staticmethod
    def clean_price_text(price_text: str) -> Optional[float]:
        """Extract price in VND from Vietnamese price text.

        Args:
            price_text: Raw price string (e.g., "2.5 tỷ", "850 triệu", "15tr/tháng")

        Returns:
            Price in VND, or None if parsing fails
        """
        if not price_text:
            return None

        price_text = price_text.lower().strip()
        price_text = price_text.replace(',', '.').replace(' ', '')

        try:
            if 'tỷ' in price_text or 'ty' in price_text:
                # "2.5ty" -> 2,500,000,000 VND
                value = float(price_text.replace('tỷ', '').replace('ty', ''))
                return value * 1_000_000_000
            elif 'triệu' in price_text or 'tr' in price_text or 'tri' in price_text:
                # "850tri" or "15tr" -> 850,000,000 or 15,000,000 VND
                value = float(price_text.replace('triệu', '').replace('tri', '').replace('tr', ''))
                return value * 1_000_000
            elif 'nghìn' in price_text or 'ngàn' in price_text or 'k' in price_text:
                # "15k" -> 15,000 VND (usually for rent)
                value = float(price_text.replace('nghìn', '').replace('ngàn', '').replace('k', ''))
                return value * 1_000
            else:
                # Try parsing as plain number
                value = float(price_text)
                return value
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def clean_area_text(area_text: str) -> Optional[float]:
        """Extract area in square meters from Vietnamese area text.

        Args:
            area_text: Raw area string (e.g., "85m2", "85m²", "85 mét vuông")

        Returns:
            Area in m2, or None if parsing fails
        """
        if not area_text:
            return None

        area_text = area_text.lower().strip()
        area_text = area_text.replace(',', '.')

        try:
            # Remove units
            for unit in ['m2', 'm²', 'mét vuông', 'm vuong', 'mx', 'm ']:
                area_text = area_text.replace(unit, ' ')

            # Extract first number found
            import re
            match = re.search(r'(\d+\.?\d*)', area_text)
            if match:
                return float(match.group(1))
            return None
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """Extract Vietnamese phone number from text.

        Args:
            text: Text containing phone number

        Returns:
            Phone number string, or None if not found
        """
        import re
        # Vietnamese mobile patterns: 09xx, 03xx, 07xx, 05xx, 08xx
        pattern = r'(0[93578]\d{8})'
        match = re.search(pattern, text.replace(' ', ''))
        return match.group(1) if match else None
