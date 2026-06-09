"""Price trend analysis for real estate market monitoring."""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


class PriceTrendAnalyzer:
    """Analyze price trends for properties by district/ward."""

    def __init__(self):
        """Initialize price trend analyzer."""
        self.price_history = defaultdict(list)  # (district, property_type) -> [(date, price, area)]
        self.trend_cache = {}

    def add_listing_data(self, listing_data: Dict[str, Any]):
        """Add listing data to price history.

        Args:
            listing_data: Listing dictionary with price, area, district, etc.
        """
        district = listing_data.get('district', 'Unknown')
        property_type = listing_data.get('property_type', 'Unknown')
        price_vnd = listing_data.get('price_vnd')
        area_m2 = listing_data.get('area_m2')
        posted_date = listing_data.get('posted_date') or datetime.now()

        if price_vnd and area_m2:
            key = (district, property_type)
            price_per_m2 = price_vnd / area_m2

            self.price_history[key].append((posted_date, price_vnd, area_m2, price_per_m2))

    def calculate_rolling_average(
        self,
        district: str,
        property_type: str,
        window_days: int = 30
    ) -> Optional[Dict[str, float]]:
        """Calculate rolling average prices.

        Args:
            district: District name
            property_type: Property type
            window_days: Rolling window in days

        Returns:
            Dict with statistics or None
        """
        key = (district, property_type)
        if key not in self.price_history:
            return None

        # Filter data within window
        cutoff_date = datetime.now() - timedelta(days=window_days)
        recent_data = [
            (price, area) for date, price, area, _ in self.price_history[key]
            if date >= cutoff_date
        ]

        if not recent_data:
            return None

        # Calculate statistics
        prices = [price for price, _ in recent_data]
        areas = [area for _, area in recent_data]
        price_per_m2_list = [price / area if area > 0 else 0 for price, area in recent_data]

        return {
            'avg_price': statistics.mean(prices),
            'median_price': statistics.median(prices),
            'avg_area': statistics.mean(areas),
            'avg_price_per_m2': statistics.mean(price_per_m2_list),
            'min_price': min(prices),
            'max_price': max(prices),
            'sample_count': len(prices)
        }

    def detect_price_anomalies(
        self,
        listing_price: float,
        listing_area: float,
        district: str,
        property_type: str,
        threshold_std: float = 2.0
    ) -> Dict[str, Any]:
        """Detect if listing price is anomalous compared to market.

        Args:
            listing_price: Listing price in VND
            listing_area: Area in m2
            district: District name
            property_type: Property type
            threshold_std: Number of standard deviations for anomaly

        Returns:
            Dict with anomaly analysis
        """
        stats = self.calculate_rolling_average(district, property_type)

        if not stats:
            return {
                'is_anomalous': False,
                'reason': 'Insufficient market data'
            }

        listing_price_per_m2 = listing_price / listing_area if listing_area > 0 else 0
        market_avg_per_m2 = stats['avg_price_per_m2']

        # Calculate deviation
        if stats.get('sample_count', 0) < 5:
            return {
                'is_anomalous': False,
                'reason': 'Insufficient market data',
                'market_avg': market_avg_per_m2,
                'listing_price_per_m2': listing_price_per_m2
            }

        # Calculate standard deviation
        key = (district, property_type)
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_prices = [
            price / area if area > 0 else 0
            for date, price, area, _ in self.price_history[key]
            if date >= cutoff_date
        ]

        if len(recent_prices) < 2:
            std_dev = 0
        else:
            std_dev = statistics.stdev(recent_prices)

        # Check for anomaly
        z_score = (listing_price_per_m2 - market_avg_per_m2) / std_dev if std_dev > 0 else 0

        is_anomalous = abs(z_score) > threshold_std

        return {
            'is_anomalous': is_anomalous,
            'z_score': z_score,
            'market_avg_per_m2': market_avg_per_m2,
            'listing_price_per_m2': listing_price_per_m2,
            'deviation_percent': ((listing_price_per_m2 - market_avg_per_m2) / market_avg_per_m2 * 100) if market_avg_per_m2 > 0 else 0,
            'sample_count': stats['sample_count']
        }

    def get_trend_direction(
        self,
        district: str,
        property_type: str,
        period_days: int = 30
    ) -> Optional[str]:
        """Determine price trend direction.

        Args:
            district: District name
            property_type: Property type
            period_days: Period to analyze

        Returns:
            Trend direction: 'rising', 'falling', 'stable', or None
        """
        key = (district, property_type)
        if key not in self.price_history:
            return None

        now = datetime.now()
        mid_period = now - timedelta(days=period_days // 2)
        start_period = now - timedelta(days=period_days)

        # Split into two periods
        recent_prices = []
        older_prices = []

        for date, price, area, _ in self.price_history[key]:
            if date >= mid_period:
                recent_prices.append(price / area if area > 0 else 0)
            elif date >= start_period:
                older_prices.append(price / area if area > 0 else 0)

        if not recent_prices or not older_prices:
            return None

        # Compare averages
        recent_avg = statistics.mean(recent_prices)
        older_avg = statistics.mean(older_prices)

        # Calculate percent change
        if older_avg > 0:
            change = (recent_avg - older_avg) / older_avg * 100
        else:
            change = 0

        if change > 5:
            return 'rising'
        elif change < -5:
            return 'falling'
        else:
            return 'stable'

    def generate_market_report(
        self,
        districts: List[str],
        property_types: List[str],
        period_days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """Generate comprehensive market report.

        Args:
            districts: List of districts to include
            property_types: List of property types to include
            period_days: Analysis period

        Returns:
            Dict of district -> property_type -> report data
        """
        report = {}

        for district in districts:
            report[district] = {}

            for prop_type in property_types:
                stats = self.calculate_rolling_average(district, prop_type, period_days)
                trend = self.get_trend_direction(district, prop_type, period_days)

                if stats:
                    report[district][prop_type] = {
                        **stats,
                        'trend': trend,
                        'period_days': period_days
                    }

        return report

    def export_history(self, filepath: str):
        """Export price history to CSV.

        Args:
            filepath: Path to save CSV file
        """
        import csv

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['district', 'property_type', 'date', 'price_vnd', 'area_m2', 'price_per_m2'])

            for key, data in self.price_history.items():
                district, property_type = key
                for date, price, area, price_per_m2 in data:
                    writer.writerow([district, property_type, date.isoformat(), price, area, price_per_m2])

        logger.info(f"Exported price history to {filepath}")

    def get_district_rankings(self, property_type: str, metric: str = 'avg_price_per_m2') -> List[Tuple[str, float]]:
        """Rank districts by a metric.

        Args:
            property_type: Property type to analyze
            metric: Metric to rank by

        Returns:
            List of (district, value) tuples sorted by value
        """
        district_values = []

        for (district, prop_type), _ in self.price_history.items():
            if prop_type == property_type:
                stats = self.calculate_rolling_average(district, property_type)
                if stats and metric in stats:
                    district_values.append((district, stats[metric]))

        # Sort by value descending
        district_values.sort(key=lambda x: x[1], reverse=True)

        return district_values
