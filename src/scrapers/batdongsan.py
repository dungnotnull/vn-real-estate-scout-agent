"""Batdongsan.com.vn scraper implementation using crawl4ai."""
from typing import List, Optional, Dict, Any
import re
import hashlib
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
import json
import asyncio
from .base import BaseScraper, ScrapedListing
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import logging

logger = logging.getLogger(__name__)


class BatdongsanScraper(BaseScraper):
    """Scraper for Batdongsan.com.vn with full crawl4ai integration."""

    BASE_URL = "https://batdongsan.com.vn"
    SEARCH_PATHS = {
        "buy": "/ban-nha-dat",
        "rent": "/cho-thue-nha-dat"
    }

    PROPERTY_TYPE_SLUGS = {
        "apartment": "can-ho-chung-cu",
        "house": "nha-rieng",
        "villa": "biet-thu",
        "land": "dat",
        "commercial": "bat-dong-san-khac"
    }

    CITY_SLUGS = {
        "ho chi minh": "ho-chi-minh",
        "hcmc": "ho-chi-minh",
        "hanoi": "ha-noi",
        "ha noi": "ha-noi",
        "da nang": "da-nang",
        "hai phong": "hai-phong",
        "can tho": "can-tho",
        "hue": "thua-thien-hue"
    }

    def __init__(self):
        """Initialize Batdongsan scraper."""
        super().__init__("batdongsan")
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.crawler_config = CrawlerRunConfig(
            word_count_threshold=10,
            extraction_strategy=None,
            bypass_cache=True,
            js_code="""
            async function() {
                await new Promise(resolve => setTimeout(resolve, 2000));
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            """
        )

    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from Batdongsan URL."""
        patterns = [
            r'/pr(\d+)',
            r'/(\d+)/[a-z-]+$',
            r'id=([^&]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return self._generate_listing_id(url)

    def _build_search_url(self, **params) -> str:
        """Build search URL from parameters."""
        listing_type = params.get('listing_type', 'buy')
        base_path = self.SEARCH_PATHS.get(listing_type, self.SEARCH_PATHS['buy'])

        parts = [base_path]
        city = params.get('city', '').lower()
        if city:
            city_slug = self.CITY_SLUGS.get(city)
            if city_slug:
                parts.append(city_slug)

        property_type = params.get('property_type', '').lower()
        if property_type:
            type_slug = self.PROPERTY_TYPE_SLUGS.get(property_type)
            if type_slug:
                parts.append(type_slug)

        path = '/'.join(parts)
        query_params = []

        if 'min_price' in params:
            query_params.append(f"mins={params['min_price']}")
        if 'max_price' in params:
            query_params.append(f"maxs={params['max_price']}")
        if 'min_area' in params:
            query_params.append(f"mina={params['min_area']}")
        if 'max_area' in params:
            query_params.append(f"maxa={params['max_area']}")
        if 'bedrooms' in params:
            query_params.append(f"nb={params['bedrooms']}")

        query = '&'.join(query_params)
        return f"{self.BASE_URL}{path}?{query}" if query else f"{self.BASE_URL}{path}"

    async def search_listings(self, **search_params) -> List[ScrapedListing]:
        """Search for listings on Batdongsan."""
        search_url = self._build_search_url(**search_params)
        logger.info(f"Searching Batdongsan: {search_url}")

        listings = []
        page = 1
        max_pages = search_params.get('max_pages', 5)

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            while page <= max_pages:
                page_url = f"{search_url}&p={page}" if page > 1 else search_url

                try:
                    result = await crawler.arun(
                        url=page_url,
                        config=self.crawler_config
                    )

                    if not result.success:
                        logger.warning(f"Failed to fetch page {page}: {result.error_message}")
                        break

                    page_listings = self._parse_search_results(result.html, page_url)
                    if not page_listings:
                        logger.info(f"No more listings found on page {page}")
                        break

                    listings.extend(page_listings)
                    logger.info(f"Found {len(page_listings)} listings on page {page}")
                    page += 1

                except Exception as e:
                    logger.error(f"Error scraping page {page}: {e}")
                    break

        logger.info(f"Total listings found: {len(listings)}")
        return listings

    def _parse_search_results(self, html: str, page_url: str) -> List[ScrapedListing]:
        """Parse listing URLs from search results."""
        from bs4 import BeautifulSoup
        import time

        listings = []
        soup = BeautifulSoup(html, 'html.parser')

        listing_elements = soup.select('.product-item') or soup.select('[class*="listing"]')

        for element in listing_elements:
            try:
                link_elem = element.find('a', href=True) or element.select_one('a[href*="/pr"]')
                if not link_elem:
                    continue

                url = link_elem.get('href')
                if not url or url.startswith('javascript'):
                    continue

                if not url.startswith('http'):
                    url = urljoin(self.BASE_URL, url)

                # Extract basic info from search result
                title_elem = element.select_one('.product-title') or element.select_one('h3')
                price_elem = element.select_one('.product-price') or element.select_one('[class*="price"]')
                area_elem = element.select_one('.product-area') or element.select_one('[class*="area"]')

                title = title_elem.get_text(strip=True) if title_elem else ""
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                area_text = area_elem.get_text(strip=True) if area_elem else ""

                listing_id = self._extract_listing_id(url)

                listing = ScrapedListing(
                    id=listing_id,
                    platform=self.platform_name,
                    url=url,
                    title=title,
                    description=title,
                    price_vnd=self.clean_price_text(price_text),
                    area_m2=self.clean_area_text(area_text),
                    property_type=None,
                    bedrooms=None,
                    address_raw=None,
                    contact_phone=None,
                    contact_name=None,
                    posted_date=datetime.now(),
                    images=[],
                    amenities=[],
                    legal_status=None
                )

                listings.append(listing)

            except Exception as e:
                logger.debug(f"Error parsing listing element: {e}")
                continue

        return listings

    async def get_listing_details(self, listing_id: str) -> Optional[ScrapedListing]:
        """Get detailed listing information."""
        if not listing_id:
            return None

        url = f"{self.BASE_URL}/pr-{listing_id}"

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            try:
                result = await crawler.arun(
                    url=url,
                    config=self.crawler_config
                )

                if not result.success:
                    logger.error(f"Failed to fetch listing {listing_id}: {result.error_message}")
                    return None

                return self._parse_listing_page(result.html, url, listing_id)

            except Exception as e:
                logger.error(f"Error fetching listing {listing_id}: {e}")
                return None

    def _parse_listing_page(self, html: str, url: str, listing_id: str) -> Optional[ScrapedListing]:
        """Parse listing detail page."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        try:
            # Title
            title_elem = soup.select_one('.product-title') or soup.select_one('h1')
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Description
            desc_elem = soup.select_one('.product-description') or soup.select_one('[class*="description"]')
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Price
            price_elem = soup.select_one('.product-price') or soup.select_one('[class*="price"]')
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            price_vnd = self.clean_price_text(price_text)

            # Area
            area_elem = soup.select_one('.product-area') or soup.select_one('[class*="area"]')
            area_text = area_elem.get_text(strip=True) if area_elem else ""
            area_m2 = self.clean_area_text(area_text)

            # Address
            address_elem = soup.select_one('.product-address') or soup.select_one('[class*="address"]')
            address_raw = address_elem.get_text(strip=True) if address_elem else None

            # Bedrooms
            bedrooms = None
            bedroom_elem = soup.select_one('[class*="bedroom"]') or soup.select_one('.bedroom')
            if bedroom_elem:
                bedroom_text = bedroom_elem.get_text(strip=True)
                bedroom_match = re.search(r'(\d+)', bedroom_text)
                if bedroom_match:
                    bedrooms = int(bedroom_match.group(1))

            # Bathrooms
            bathrooms = None
            bathroom_elem = soup.select_one('[class*="bathroom"]') or soup.select_one('.bathroom')
            if bathroom_elem:
                bathroom_text = bathroom_elem.get_text(strip=True)
                bathroom_match = re.search(r'(\d+)', bathroom_text)
                if bathroom_match:
                    bathrooms = int(bathroom_match.group(1))

            # Contact info
            contact_phone = None
            contact_name = None

            phone_elem = soup.select_one('.product-phone') or soup.select_one('[class*="phone"]')
            if phone_elem:
                phone_text = phone_elem.get_text(strip=True)
                contact_phone = self.extract_phone(phone_text)

            name_elem = soup.select_one('.product-contact-name') or soup.select_one('[class*="contact"]')
            if name_elem:
                contact_name = name_elem.get_text(strip=True)

            # Legal status
            legal_status = None
            legal_elem = soup.select_one('[class*="legal"]') or soup.select_one('.juridical')
            if legal_elem:
                legal_text = legal_elem.get_text(strip=True).lower()
                if 'sổ hồng' in legal_text or 'sh' in legal_text:
                    legal_status = 'SHR'
                elif 'sổ đỏ' in legal_text or 'sd' in legal_text:
                    legal_status = 'SD'

            # Images
            images = []
            img_elems = soup.select('.product-gallery img') or soup.select('[class*="image"] img')
            for img_elem in img_elems[:10]:
                img_url = img_elem.get('src') or img_elem.get('data-src')
                if img_url:
                    if not img_url.startswith('http'):
                        img_url = urljoin(self.BASE_URL, img_url)
                    images.append(img_url)

            # Property type from URL or breadcrumbs
            property_type = "apartment"
            breadcrumb = soup.select('.breadcrumb a')
            if breadcrumb:
                breadcrumb_text = ' '.join([a.get_text().lower() for a in breadcrumb])
                if 'căn hộ' in breadcrumb_text or 'chung cư' in breadcrumb_text:
                    property_type = "apartment"
                elif 'nhà riêng' in breadcrumb_text or 'nhà phố' in breadcrumb_text:
                    property_type = "house"
                elif 'biệt thự' in breadcrumb_text:
                    property_type = "villa"
                elif 'đất' in breadcrumb_text:
                    property_type = "land"

            return ScrapedListing(
                id=listing_id,
                platform=self.platform_name,
                url=url,
                title=title,
                description=description,
                price_vnd=price_vnd,
                area_m2=area_m2,
                property_type=property_type,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                address_raw=address_raw,
                contact_phone=contact_phone,
                contact_name=contact_name,
                posted_date=datetime.now(),
                images=images,
                amenities=[],
                legal_status=legal_status,
                latitude=None,
                longitude=None,
                is_verified=False,
                source_html=html
            )

        except Exception as e:
            logger.error(f"Error parsing listing page: {e}")
            return None

    async def scrape_with_retry(self, url: str, max_retries: int = 3) -> Optional[ScrapedListing]:
        """Scrape a listing with retry logic."""
        listing_id = self._extract_listing_id(url)

        for attempt in range(max_retries):
            try:
                listing = await self.get_listing_details(listing_id)
                if listing:
                    return listing
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")

        logger.error(f"All {max_retries} attempts failed for {url}")
        return None


class ChototScraper(BaseScraper):
    """Scraper for Chotot.com with full crawl4ai integration."""

    BASE_URL = "https://www.chotot.com"

    def __init__(self):
        """Initialize Chotot scraper."""
        super().__init__("chotot")
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.crawler_config = CrawlerRunConfig(
            word_count_threshold=10,
            bypass_cache=True,
            js_code="""
            async function() {
                await new Promise(resolve => setTimeout(resolve, 2000));
                window.scrollTo(0, document.body.scrollHeight);
            }
            """
        )

    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from Chotot URL."""
        patterns = [
            r'/(\d+)\.htm',
            r'id=([^&]+)',
            r'/sa[-_]?(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return self._generate_listing_id(url)

    async def search_listings(self, **search_params) -> List[ScrapedListing]:
        """Search for listings on Chotot."""
        search_url = self._build_search_url(**search_params)
        logger.info(f"Searching Chotot: {search_url}")

        listings = []
        page = 1
        max_pages = search_params.get('max_pages', 5)

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            while page <= max_pages:
                try:
                    result = await crawler.arun(
                        url=search_url,
                        config=self.crawler_config
                    )

                    if not result.success:
                        logger.warning(f"Failed to fetch page {page}: {result.error_message}")
                        break

                    page_listings = self._parse_search_results(result.html)
                    if not page_listings:
                        break

                    listings.extend(page_listings)
                    logger.info(f"Found {len(page_listings)} listings on page {page}")
                    page += 1

                except Exception as e:
                    logger.error(f"Error scraping Chotot: {e}")
                    break

        return listings

    def _build_search_url(self, **params) -> str:
        """Build Chotot search URL."""
        base_path = "/mua-ban-bat-dong-san"

        city_map = {
            "ho chi minh": "ho_chi_minh",
            "hanoi": "ha_noi",
            "da nang": "da_nang",
            "hai phong": "hai_phong"
        }

        city = params.get('city', '').lower()
        if city in city_map:
            base_path = f"/{city_map[city]}{base_path}"

        return f"{self.BASE_URL}{base_path}"

    def _parse_search_results(self, html: str) -> List[ScrapedListing]:
        """Parse Chotot search results."""
        from bs4 import BeautifulSoup

        listings = []
        soup = BeautifulSoup(html, 'html.parser')

        ad_elements = soup.select('.AdItem') or soup.select('[class*="adItem"]')

        for element in ad_elements:
            try:
                link_elem = element.find('a', href=True)
                if not link_elem:
                    continue

                url = link_elem.get('href')
                if not url.startswith('http'):
                    url = urljoin(self.BASE_URL, url)

                title_elem = element.select_one('.adItem___title') or element.select_one('[class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else ""

                price_elem = element.select_one('.adItem___price') or element.select_one('[class*="price"]')
                price_text = price_elem.get_text(strip=True) if price_elem else ""

                listing_id = self._extract_listing_id(url)

                listing = ScrapedListing(
                    id=listing_id,
                    platform=self.platform_name,
                    url=url,
                    title=title,
                    description=title,
                    price_vnd=self.clean_price_text(price_text),
                    property_type=None
                )

                listings.append(listing)

            except Exception as e:
                logger.debug(f"Error parsing Chotot listing: {e}")
                continue

        return listings

    async def get_listing_details(self, listing_id: str) -> Optional[ScrapedListing]:
        """Get detailed listing information from Chotot."""
        url = f"{self.BASE_URL}/sa-{listing_id}.htm"

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            try:
                result = await crawler.arun(url=url, config=self.crawler_config)

                if not result.success:
                    return None

                return self._parse_listing_page(result.html, url, listing_id)

            except Exception as e:
                logger.error(f"Error fetching Chotot listing: {e}")
                return None

    def _parse_listing_page(self, html: str, url: str, listing_id: str) -> Optional[ScrapedListing]:
        """Parse Chotot listing detail page."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        try:
            title_elem = soup.select_one('.adPage___title') or soup.select_one('h1')
            title = title_elem.get_text(strip=True) if title_elem else ""

            desc_elem = soup.select_one('.adPage___description') or soup.select_one('[class*="description"]')
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            price_elem = soup.select_one('.adPage___price') or soup.select_one('[class*="price"]')
            price_text = price_elem.get_text(strip=True) if price_elem else ""

            return ScrapedListing(
                id=listing_id,
                platform=self.platform_name,
                url=url,
                title=title,
                description=description,
                price_vnd=self.clean_price_text(price_text),
                property_type=None,
                images=[],
                source_html=html
            )

        except Exception as e:
            logger.error(f"Error parsing Chotot listing page: {e}")
            return None
