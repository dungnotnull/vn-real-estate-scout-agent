"""Vietnamese address parsing and geocoding normalization."""
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import re
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)


@dataclass
class ParsedAddress:
    """Parsed Vietnamese address components."""
    raw_address: str
    street: Optional[str] = None
    ward: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Vietnam"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class GeocodedAddress:
    """Address with geocoding results."""
    parsed: ParsedAddress
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None
    place_id: Optional[str] = None
    geocoding_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = self.parsed.to_dict()
        result.update({
            'latitude': self.latitude,
            'longitude': self.longitude,
            'formatted_address': self.formatted_address,
            'place_id': self.place_id,
            'geocoding_confidence': self.geocoding_confidence
        })
        return {k: v for k, v in result.items() if v is not None}


class VietnameseAddressParser:
    """Parse and normalize Vietnamese addresses with real model integration."""

    WARD_PREFIXES = ['phường', 'phuờng', 'p.', 'xã', 'x.', 'thôn', 't.', 'ấp']
    DISTRICT_PREFIXES = ['quận', 'q.', 'huyện', 'h.', 'thị xã', 'tx.']
    CITY_PREFIXES = ['thành phố', 'tp.', 'tỉnh', 't.']

    MAJOR_CITIES = {
        'hồ chí minh': 'Ho Chi Minh City',
        'hcmc': 'Ho Chi Minh City',
        'thành phố hồ chí minh': 'Ho Chi Minh City',
        'hà nội': 'Hanoi',
        'ha noi': 'Hanoi',
        'thành phố hà nội': 'Hanoi',
        'đà nẵng': 'Da Nang',
        'da nang': 'Da Nang',
        'thành phố đà nẵng': 'Da Nang',
        'hải phòng': 'Hai Phong',
        'hai phong': 'Hai Phong',
        'cần thơ': 'Can Tho',
        'can tho': 'Can Tho',
    }

    def __init__(self, model_name: str = "rainote/vn-address-ner", use_model: bool = False):
        """Initialize address parser."""
        self.model_name = model_name
        self.use_model = use_model
        self.pipeline = None

    def load_model(self) -> bool:
        """Load the address NER model."""
        if not self.use_model:
            logger.info("Using rule-based address parsing")
            return True

        try:
            logger.info(f"Loading address NER model: {self.model_name}")
            self.pipeline = pipeline("token-classification", model=self.model_name)
            logger.info("Address NER model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load address NER model: {e}")
            return False

    def parse(self, address: str) -> ParsedAddress:
        """Parse a Vietnamese address into components."""
        if self.pipeline and self.use_model:
            return self._model_parse(address)
        return self._rule_based_parse(address)

    def _model_parse(self, address: str) -> ParsedAddress:
        """Parse address using NER model."""
        try:
            entities = self.pipeline(address)

            result = ParsedAddress(raw_address=address)

            current_type = None
            current_text = []

            for entity in entities:
                entity_type = entity.get('entity', 'O')
                word = entity.get('word', '')

                if entity_type.startswith('B-'):
                    if current_type and current_text:
                        self._assign_component(result, current_type, ' '.join(current_text))
                    current_type = entity_type[2:]
                    current_text = [word]
                elif entity_type.startswith('I-') and current_type:
                    current_text.append(word)
                else:
                    if current_type and current_text:
                        self._assign_component(result, current_type, ' '.join(current_text))
                    current_type = None
                    current_text = []

            if current_type and current_text:
                self._assign_component(result, current_type, ' '.join(current_text))

            return result

        except Exception as e:
            logger.error(f"Error in model-based parsing: {e}")
            return self._rule_based_parse(address)

    def _assign_component(self, result: ParsedAddress, component_type: str, text: str):
        """Assign parsed text to address component."""
        component_type = component_type.lower()
        if 'street' in component_type or 'đường' in component_type:
            result.street = text
        elif 'ward' in component_type or 'xã' in component_type or 'phường' in component_type:
            result.ward = text
        elif 'district' in component_type or 'huyện' in component_type or 'quận' in component_type:
            result.district = text
        elif 'city' in component_type or 'thành phố' in component_type or 'tỉnh' in component_type:
            result.city = self._normalize_city(text)

    def _rule_based_parse(self, address: str) -> ParsedAddress:
        """Parse address using rule-based component extraction."""
        address_lower = address.lower()
        result = ParsedAddress(raw_address=address)

        # Extract city
        for city_key, city_name in self.MAJOR_CITIES.items():
            if city_key in address_lower:
                result.city = city_name
                break

        # Extract ward
        ward_pattern = r'(' + '|'.join(self.WARD_PREFIXES) + r')\s+([\w\s]+?)(?:,|$|\s+quận|\s+huyện)'
        ward_match = re.search(ward_pattern, address_lower)
        if ward_match:
            result.ward = ward_match.group(2).strip().title()

        # Extract district
        district_pattern = r'(' + '|'.join(self.DISTRICT_PREFIXES) + r')\s+([\w\s]+?)(?:,|$|\s+thành phố|\s+tỉnh)'
        district_match = re.search(district_pattern, address_lower)
        if district_match:
            result.district = district_match.group(2).strip().title()

        # Extract street
        if not result.ward and not result.district:
            street_pattern = r'(đường|đg|d\.|số)\s+([\w\s]+?)(?:,|$)'
            street_match = re.search(street_pattern, address_lower)
            if street_match:
                result.street = street_match.group(2).strip().title()

        return result

    def _normalize_city(self, city: str) -> str:
        """Normalize city name."""
        city_lower = city.lower()
        for key, value in self.MAJOR_CITIES.items():
            if key in city_lower:
                return value
        return city.title()

    def geocode(self, parsed_address: ParsedAddress, api_key: Optional[str] = None) -> GeocodedAddress:
        """Convert parsed address to coordinates using Google Maps Geocoding API."""
        if not api_key:
            logger.warning("No Google Maps API key provided")
            return GeocodedAddress(parsed=parsed_address)

        try:
            import googlemaps
            gmaps = googlemaps.Client(key=api_key)

            address_str = parsed_address.raw_address
            geocode_result = gmaps.geocode(address_str)

            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                return GeocodedAddress(
                    parsed=parsed_address,
                    latitude=location['lat'],
                    longitude=location['lng'],
                    formatted_address=geocode_result[0]['formatted_address'],
                    place_id=geocode_result[0].get('place_id'),
                    geocoding_confidence=0.9
                )

        except Exception as e:
            logger.error(f"Geocoding failed: {e}")

        return GeocodedAddress(parsed=parsed_address)

    def batch_parse(self, addresses: List[str]) -> List[ParsedAddress]:
        """Parse multiple addresses."""
        return [self.parse(addr) for addr in addresses]

    def __enter__(self):
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
