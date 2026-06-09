"""Weighted scoring engine for property ranking."""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PropertyScore:
    """Individual scoring component."""
    component: str  # price, commute, area, legal, authenticity, amenities
    score: float  # 0-1
    weight: float  # 0-1
    weighted_score: float  # score * weight
    reason: Optional[str] = None


@dataclass
class RankedProperty:
    """Property with complete scoring breakdown."""
    property_id: str
    listing_id: str
    total_score: float  # 0-1, weighted sum
    scores: List[PropertyScore]
    property_data: Dict[str, Any]
    is_genuine: bool
    flags: List[str]  # Warnings (flood risk, suspected fake, etc.)

    def __post_init__(self):
        if self.flags is None:
            self.flags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'property_id': self.property_id,
            'listing_id': self.listing_id,
            'total_score': self.total_score,
            'scores': [
                {
                    'component': s.component,
                    'score': s.score,
                    'weight': s.weight,
                    'weighted_score': s.weighted_score,
                    'reason': s.reason
                }
                for s in self.scores
            ],
            'property_data': self.property_data,
            'is_genuine': self.is_genuine,
            'flags': self.flags
        }


class PropertyRanker:
    """Weighted scoring engine for property ranking.

    Scoring weights (configurable):
    - Price fit: 30%
    - Commute: 25%
    - Area fit: 15%
    - Legal status: 15%
    - Authenticity: 10%
    - Amenities: 5%
    """

    # Default weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        'price': 0.30,
        'commute': 0.25,
        'area': 0.15,
        'legal': 0.15,
        'authenticity': 0.10,
        'amenities': 0.05,
    }

    # Score thresholds
    HIGH_SCORE_THRESHOLD = 0.75
    ACCEPTABLE_SCORE_THRESHOLD = 0.60

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize ranker with custom weights.

        Args:
            weights: Custom weight dictionary (keys must match DEFAULT_WEIGHTS)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()

    def _validate_weights(self):
        """Ensure weights sum to 1.0 and all keys exist."""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total}, normalizing")
            for key in self.weights:
                self.weights[key] /= total

    def rank_property(
        self,
        property_data: Dict[str, Any],
        user_preferences: Dict[str, Any],
        commute_score: Optional[float] = None,
        flood_info: Optional[Dict[str, Any]] = None
    ) -> RankedProperty:
        """Calculate weighted score for a property.

        Args:
            property_data: Property listing data
            user_preferences: User search preferences
            commute_score: Pre-calculated commute score (0-1)
            flood_info: Flood zone information

        Returns:
            RankedProperty with complete scoring breakdown
        """
        scores = []
        flags = []

        # Price fit (30%)
        price_score = self._score_price_fit(
            property_data.get('price_vnd'),
            user_preferences.get('min_price'),
            user_preferences.get('max_price')
        )
        scores.append(PropertyScore(
            component='price',
            score=price_score,
            weight=self.weights['price'],
            weighted_score=price_score * self.weights['price'],
            reason=f"Price {property_data.get('price_vnd', 0):,.0f} VND vs budget {user_preferences.get('max_price', 0):,.0f} VND"
        ))

        # Commute (25%)
        if commute_score is not None:
            scores.append(PropertyScore(
                component='commute',
                score=commute_score,
                weight=self.weights['commute'],
                weighted_score=commute_score * self.weights['commute'],
                reason=f"Commute score {commute_score:.2f}"
            ))
        else:
            scores.append(PropertyScore(
                component='commute',
                score=0.5,  # Neutral score if no data
                weight=self.weights['commute'],
                weighted_score=0.5 * self.weights['commute'],
                reason="No commute data available"
            ))

        # Area fit (15%)
        area_score = self._score_area_fit(
            property_data.get('area_m2'),
            user_preferences.get('min_area'),
            user_preferences.get('max_area')
        )
        scores.append(PropertyScore(
            component='area',
            score=area_score,
            weight=self.weights['area'],
            weighted_score=area_score * self.weights['area'],
            reason=f"Area {property_data.get('area_m2', 0)} m2 vs desired {user_preferences.get('min_area', 0)}-{user_preferences.get('max_area', 0)} m2"
        ))

        # Legal status (15%)
        legal_score = self._score_legal_status(
            property_data.get('legal_status'),
            user_preferences.get('legal_status_required')
        )
        scores.append(PropertyScore(
            component='legal',
            score=legal_score,
            weight=self.weights['legal'],
            weighted_score=legal_score * self.weights['legal'],
            reason=f"Legal status: {property_data.get('legal_status', 'Unknown')}"
        ))

        # Authenticity (10%)
        authenticity_score = self._score_authenticity(
            property_data.get('authenticity_score', 0),
            property_data.get('is_verified', False)
        )
        if authenticity_score < 0.5:
            flags.append("Suspected fake or duplicate listing")
        scores.append(PropertyScore(
            component='authenticity',
            score=authenticity_score,
            weight=self.weights['authenticity'],
            weighted_score=authenticity_score * self.weights['authenticity'],
            reason=f"Authenticity score {authenticity_score:.2f}"
        ))

        # Amenities (5%)
        amenities_score = self._score_amenities(
            property_data.get('amenities', []),
            user_preferences.get('must_haves', []),
            property_data.get('bedrooms', 0),
            user_preferences.get('bedrooms_min', 0)
        )
        scores.append(PropertyScore(
            component='amenities',
            score=amenities_score,
            weight=self.weights['amenities'],
            weighted_score=amenities_score * self.weights['amenities'],
            reason=f"Amenities match score {amenities_score:.2f}"
        ))

        # Flood risk flag
        if flood_info:
            flood_risk = flood_info.get('flood_risk', 'UNKNOWN')
            if flood_risk in ['MEDIUM', 'HIGH']:
                flags.append(f"Flood risk: {flood_risk}")
                # Penalty for flood risk
                flood_penalty = 0.3 if flood_risk == 'HIGH' else 0.1
                for score in scores:
                    if score.component in ['price', 'commute', 'area']:
                        score.score = max(0, score.score - flood_penalty)
                        score.weighted_score = score.score * score.weight

        # Calculate total score
        total_score = sum(s.weighted_score for s in scores)

        # Determine if genuine
        is_genuine = (
            property_data.get('authenticity_score', 0) > 0.5 and
            property_data.get('authenticity_score', 1) != 0
        )

        return RankedProperty(
            property_id=property_data.get('property_id', ''),
            listing_id=property_data.get('listing_id', ''),
            total_score=total_score,
            scores=scores,
            property_data=property_data,
            is_genuine=is_genuine,
            flags=flags
        )

    def _score_price_fit(self, price: Optional[float], min_budget: Optional[float], max_budget: Optional[float]) -> float:
        """Score price fit (0-1).

        Perfect score: within budget
        Linear decay: 20% over budget = 0 score
        """
        if price is None or max_budget is None:
            return 0.5  # Neutral if no data

        if min_budget and price < min_budget:
            # Under minimum budget - suspicious or very old
            return 0.3

        if price <= max_budget:
            return 1.0

        # Over budget - linear decay
        over_budget = (price - max_budget) / max_budget
        if over_budget > 0.2:  # More than 20% over
            return 0.0
        return 1.0 - (over_budget / 0.2)

    def _score_area_fit(self, area: Optional[float], min_area: Optional[float], max_area: Optional[float]) -> float:
        """Score area fit (0-1)."""
        if area is None:
            return 0.5

        if min_area and max_area:
            if min_area <= area <= max_area:
                return 1.0
            # Calculate distance from range
            if area < min_area:
                diff = min_area - area
                return max(0, 1.0 - (diff / min_area))
            else:
                diff = area - max_area
                return max(0, 1.0 - (diff / max_area))
        elif min_area:
            return 1.0 if area >= min_area else 0.5
        elif max_area:
            return 1.0 if area <= max_area else 0.5

        return 0.5

    def _score_legal_status(self, legal_status: Optional[str], required: Optional[str]) -> float:
        """Score legal status (0-1)."""
        if not required:
            return 1.0  # No requirement

        if not legal_status:
            return 0.0  # Unknown status

        # Direct match
        if legal_status == required:
            return 1.0

        # Partial matches
        if required in ['SHR', 'SHTT'] and legal_status in ['SHR', 'SHTT']:
            return 0.8

        if required == 'dat_tho_cu' and legal_status == 'dat_tho_cu':
            return 1.0

        # Penalty for unclear status
        return 0.3

    def _score_authenticity(self, authenticity_score: float, is_verified: bool) -> float:
        """Score authenticity (0-1)."""
        if is_verified:
            return 1.0

        # Use model score if available
        if authenticity_score > 0:
            return authenticity_score

        return 0.5  # Neutral if no data

    def _score_amenities(self, amenities: List[str], must_haves: List[str], bedrooms: int, bedrooms_min: int) -> float:
        """Score amenities match (0-1)."""
        score = 0.0

        # Check bedroom requirement
        if bedrooms_min > 0:
            if bedrooms >= bedrooms_min:
                score += 0.5
            else:
                score += max(0, 0.5 * (bedrooms / bedrooms_min))

        # Check must-have amenities
        if must_haves:
            matched = sum(1 for item in must_haves if any(item.lower() in a.lower() for a in amenities))
            score += (matched / len(must_haves)) * 0.5
        else:
            score += 0.5  # Neutral if no requirements

        return min(1.0, score)

    def rank_properties(
        self,
        properties: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        commute_scores: Optional[Dict[str, float]] = None,
        flood_infos: Optional[Dict[str, Dict]] = None
    ) -> List[RankedProperty]:
        """Rank multiple properties.

        Args:
            properties: List of property data
            user_preferences: User search preferences
            commute_scores: Dict of property_id -> commute score
            flood_infos: Dict of property_id -> flood info

        Returns:
            List of RankedProperty, sorted by total_score descending
        """
        ranked = []

        for prop in properties:
            prop_id = prop.get('property_id', '')
            commute = commute_scores.get(prop_id) if commute_scores else None
            flood = flood_infos.get(prop_id) if flood_infos else None

            ranked_prop = self.rank_property(prop, user_preferences, commute, flood)
            ranked.append(ranked_prop)

        # Sort by total score descending
        ranked.sort(key=lambda x: x.total_score, reverse=True)

        return ranked

    def get_top_n(self, ranked_properties: List[RankedProperty], n: int = 5, min_score: float = 0.5) -> List[RankedProperty]:
        """Get top N properties above minimum score threshold.

        Args:
            ranked_properties: List of ranked properties (pre-sorted)
            n: Maximum number to return
            min_score: Minimum acceptable score

        Returns:
            List of top N properties meeting criteria
        """
        qualified = [p for p in ranked_properties if p.total_score >= min_score and p.is_genuine]
        return qualified[:n]
