"""XGBoost classifier for fake listing detection."""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score
import logging

logger = logging.getLogger(__name__)


class FakeListingClassifier:
    """XGBoost classifier to detect fake/duplicate listings."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize classifier."""
        self.model_path = model_path
        self.model = None
        self.feature_names = [
            'price_variance_in_cluster',
            'listing_age_days',
            'broker_account_age_days',
            'image_hash_match_count',
            'coordinate_jitter_meters',
            'description_length',
            'title_description_similarity',
            'contact_info_provided',
            'verified_status',
            'platform_reputation_score'
        ]

    def train(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> Dict[str, float]:
        """Train the XGBoost classifier.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Labels (0: GENUINE, 1: SUSPECTED_FAKE, 2: CONFIRMED_DUPLICATE)
            test_size: Proportion of data for testing

        Returns:
            Dictionary of evaluation metrics
        """
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        self.model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            use_label_encoder=False,
            eval_metric='mlogloss'
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # Evaluate
        y_pred = self.model.predict(X_test)

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'f1_macro': f1_score(y_test, y_pred, average='macro')
        }

        logger.info(f"Training metrics: {metrics}")
        return metrics

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict class for listings.

        Args:
            features: Feature matrix

        Returns:
            Array of predictions (0: GENUINE, 1: SUSPECTED_FAKE, 2: CONFIRMED_DUPLICATE)
        """
        if not self.model:
            logger.warning("Model not trained, returning GENUINE for all")
            return np.zeros(len(features), dtype=int)

        return self.model.predict(features)

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Predict class probabilities.

        Args:
            features: Feature matrix

        Returns:
            Probability array (n_samples, 3)
        """
        if not self.model:
            return np.ones((len(features), 3)) / 3

        return self.model.predict_proba(features)

    def score_listing(self, listing_data: Dict[str, Any]) -> Tuple[int, float]:
        """Score a single listing.

        Args:
            listing_data: Listing dictionary

        Returns:
            (class, confidence) tuple
        """
        features = self._extract_features(listing_data)
        features_array = np.array([list(features.values())])

        class_pred = int(self.predict(features_array)[0])
        proba = self.predict_proba(features_array)[0]
        confidence = float(proba[class_pred])

        return class_pred, confidence

    def _extract_features(self, listing: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from listing data."""
        import hashlib
        from datetime import datetime

        features = {name: 0.0 for name in self.feature_names}

        # Price variance (if cluster data available)
        if 'price_variance_in_cluster' in listing:
            features['price_variance_in_cluster'] = float(listing['price_variance_in_cluster'])

        # Listing age
        posted_date = listing.get('posted_date')
        if posted_date:
            if isinstance(posted_date, str):
                posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
            age_days = (datetime.now(posted_date.tzinfo) - posted_date).days
            features['listing_age_days'] = max(0, age_days)

        # Broker account age
        if 'broker_account_created' in listing:
            account_created = listing['broker_account_created']
            if isinstance(account_created, str):
                account_created = datetime.fromisoformat(account_created.replace('Z', '+00:00'))
            broker_age_days = (datetime.now(account_created.tzinfo) - account_created).days
            features['broker_account_age_days'] = max(0, broker_age_days)

        # Image hash matches (for duplicate detection)
        features['image_hash_match_count'] = float(listing.get('image_hash_match_count', 0))

        # Coordinate jitter
        features['coordinate_jitter_meters'] = float(listing.get('coordinate_jitter_meters', 0))

        # Description length
        description = listing.get('description', '')
        features['description_length'] = float(len(description))

        # Title-description similarity
        title = listing.get('title', '')
        if title and description:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, title, description).ratio()
            features['title_description_similarity'] = similarity

        # Contact info provided
        features['contact_info_provided'] = 1.0 if listing.get('contact_phone') else 0.0

        # Verified status
        features['verified_status'] = 1.0 if listing.get('is_verified', False) else 0.0

        # Platform reputation (placeholder)
        features['platform_reputation_score'] = float(listing.get('platform_reputation', 0.5))

        return features

    def save_model(self, path: str):
        """Save model to file."""
        if self.model:
            self.model.save_model(path)
            logger.info(f"Model saved to {path}")

    def load_model(self, path: str) -> bool:
        """Load model from file."""
        try:
            self.model = xgb.XGBClassifier()
            self.model.load_model(path)
            logger.info(f"Model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        if not self.model:
            return {}

        importance = self.model.feature_importances_
        return dict(zip(self.feature_names, importance))


class BrokerReputationScorer:
    """Score broker reputation based on historical listing quality."""

    def __init__(self):
        """Initialize reputation scorer."""
        self.reputation_scores = {}

    def update_score(self, broker_phone: str, listing_quality: float, is_fake: bool):
        """Update broker reputation score.

        Args:
            broker_phone: Broker phone number
            listing_quality: Quality score (0-1)
            is_fake: Whether listing was flagged as fake
        """
        if broker_phone not in self.reputation_scores:
            self.reputation_scores[broker_phone] = {
                'total_listings': 0,
                'genuine_count': 0,
                'fake_count': 0,
                'average_quality': 0.0,
                'reputation_score': 0.5
            }

        scores = self.reputation_scores[broker_phone]
        scores['total_listings'] += 1

        if is_fake:
            scores['fake_count'] += 1
        else:
            scores['genuine_count'] += 1

        # Update average quality
        n = scores['total_listings']
        scores['average_quality'] = (
            (scores['average_quality'] * (n - 1) + listing_quality) / n
        )

        # Calculate reputation score (0-1)
        fake_ratio = scores['fake_count'] / n if n > 0 else 0
        genuine_ratio = scores['genuine_count'] / n if n > 0 else 0

        scores['reputation_score'] = max(0, genuine_ratio - fake_ratio * 2)

    def get_score(self, broker_phone: str) -> float:
        """Get reputation score for broker.

        Args:
            broker_phone: Broker phone number

        Returns:
            Reputation score (0-1)
        """
        if broker_phone not in self.reputation_scores:
            return 0.5  # Neutral score for unknown brokers

        return self.reputation_scores[broker_phone]['reputation_score']

    def get_all_scores(self) -> Dict[str, Dict[str, Any]]:
        """Get all broker reputation scores."""
        return self.reputation_scores
