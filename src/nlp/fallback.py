"""Rule-based fallback NER extractor when PhoBERT is unavailable."""
from typing import Optional, List
import re


class FallbackExtractor:
    """Rule-based fallback extractor for Vietnamese real estate entities."""

    PRICE_PATTERNS = [
        r'(\d+[.,]?\d*)\s*(?:tỷ|ty|triệu|tr|tri)(?:\s*(?:\/|tháng)?)?',
        r'(\d+[.,]?\d*)\s*(?:nghìn|ngàn|k)'
    ]

    AREA_PATTERNS = [
        r'(\d+[.,]?\d*)\s*(?:m2|m²|mét vuông)',
    ]

    BEDROOM_PATTERNS = [
        r'(\d+)\s*(?:pn|phòng ngủ|phòng ngu)',
    ]

    BATHROOM_PATTERNS = [
        r'(\d+)\s*(?:wc|toilet|phòng vệ sinh|nền)',
    ]

    FLOOR_PATTERNS = [
        r'tầng\s*(\d+)',
        r'(\d+)\s*tầng',
    ]

    def __init__(self):
        """Initialize fallback extractor."""
        pass

    def extract(self, text: str):
        """Extract entities using rule-based patterns."""
        from .entities import NERResult, ExtractedEntity
        from ..scrapers.base import BaseScraper

        result = NERResult()
        result.entities = []

        # Extract price
        for pattern in self.PRICE_PATTERNS:
            for match in re.finditer(pattern, text.lower()):
                price = BaseScraper.clean_price_text(match.group(0))
                if price and not result.price_vnd:
                    result.price_vnd = price
                    result.entities.append(ExtractedEntity(
                        entity_type='PRICE',
                        text=match.group(0),
                        value=price,
                        confidence=0.75,
                        start=match.start(),
                        end=match.end()
                    ))
                    break

        # Extract area
        for pattern in self.AREA_PATTERNS:
            for match in re.finditer(pattern, text.lower()):
                area = BaseScraper.clean_area_text(match.group(0))
                if area and not result.area_m2:
                    result.area_m2 = area
                    result.entities.append(ExtractedEntity(
                        entity_type='AREA',
                        text=match.group(0),
                        value=area,
                        confidence=0.80,
                        start=match.start(),
                        end=match.end()
                    ))
                    break

        # Extract bedrooms
        for pattern in self.BEDROOM_PATTERNS:
            for match in re.finditer(pattern, text.lower()):
                try:
                    bedrooms = int(match.group(1))
                    if not result.bedrooms:
                        result.bedrooms = bedrooms
                        result.entities.append(ExtractedEntity(
                            entity_type='BEDROOM',
                            text=match.group(0),
                            value=bedrooms,
                            confidence=0.85,
                            start=match.start(),
                            end=match.end()
                        ))
                        break
                except ValueError:
                    pass

        # Extract bathrooms
        for pattern in self.BATHROOM_PATTERNS:
            for match in re.finditer(pattern, text.lower()):
                try:
                    bathrooms = int(match.group(1))
                    if not result.bathrooms:
                        result.bathrooms = bathrooms
                        result.entities.append(ExtractedEntity(
                            entity_type='BATHROOM',
                            text=match.group(0),
                            value=bathrooms,
                            confidence=0.85,
                            start=match.start(),
                            end=match.end()
                        ))
                        break
                except ValueError:
                    pass

        # Extract floor
        for pattern in self.FLOOR_PATTERNS:
            for match in re.finditer(pattern, text.lower()):
                try:
                    floor = int(match.group(1))
                    if not result.floor:
                        result.floor = floor
                        result.entities.append(ExtractedEntity(
                            entity_type='FLOOR',
                            text=match.group(0),
                            value=floor,
                            confidence=0.75,
                            start=match.start(),
                            end=match.end()
                        ))
                        break
                except ValueError:
                    pass

        # Extract phone
        phone = BaseScraper.extract_phone(text)
        if phone and not result.contact_phone:
            result.contact_phone = phone
            idx = text.find(phone)
            result.entities.append(ExtractedEntity(
                entity_type='PHONE',
                text=phone,
                value=phone,
                confidence=0.95,
                start=idx,
                end=idx + len(phone)
            ))

        # Extract legal status
        legal_keywords = {
            'sổ hồng riêng': 'SHR',
            'sổ hồng': 'SHTT',
            'sổ đỏ': 'SD',
            'đất thổ cư': 'dat_tho_cu',
            'chưa có sổ': 'chua_co_so'
        }
        for keyword, value in legal_keywords.items():
            if keyword in text.lower():
                result.legal_status = value
                idx = text.lower().find(keyword)
                result.entities.append(ExtractedEntity(
                    entity_type='LEGAL',
                    text=keyword,
                    value=value,
                    confidence=0.70,
                    start=idx,
                    end=idx + len(keyword)
                ))
                break

        result.model_confidence = 0.75
        return result
