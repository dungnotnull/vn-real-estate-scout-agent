"""User preference storage with encryption."""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """User search preferences for real estate."""
    # Budget
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    # Location
    preferred_cities: List[str] = None
    preferred_districts: List[str] = None
    latitude: Optional[float] = None  # Home/Work location
    longitude: Optional[float] = None
    workplace_latitude: Optional[float] = None
    workplace_longitude: Optional[float] = None

    # Property specs
    property_types: List[str] = None  # apartment, house, land, commercial
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    bedrooms_min: Optional[int] = None
    bedrooms_max: Optional[int] = None

    # Commute
    max_commute_minutes: Optional[int] = None
    commute_mode: str = "driving"  # driving, walking, cycling

    # Amenities & requirements
    must_haves: List[str] = None  # Schools, hospitals, near market, etc.
    avoid_flood_risk: bool = True
    legal_status_required: Optional[str] = None  # SHR, SHTT

    # Other
    furnished: Optional[bool] = None
    parking_required: bool = False
    verified_only: bool = True

    # Metadata
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.preferred_cities is None:
            self.preferred_cities = []
        if self.preferred_districts is None:
            self.preferred_districts = []
        if self.property_types is None:
            self.property_types = []
        if self.must_haves is None:
            self.must_haves = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SecureUserStorage:
    """Encrypted storage for user preferences using SQLite + AES-256-GCM."""

    def __init__(self, db_path: Optional[Path] = None, encryption_key: Optional[str] = None):
        """Initialize secure user storage.

        Args:
            db_path: Path to SQLite database
            encryption_key: Encryption key (or generate from env)
        """
        from src.config import USER_DATA_DIR, security

        self.db_path = db_path or (USER_DATA_DIR / "user_preferences.db")
        self.encryption_key = encryption_key or security.user_encryption_key
        self.conn = None

        if not self.encryption_key:
            logger.warning("No encryption key provided, using insecure mode")

    def _get_encryption_key(self) -> bytes:
        """Derive encryption key from passphrase.

        Returns:
            32-byte key for AES-256
        """
        if not self.encryption_key:
            raise ValueError("No encryption key available")

        # Derive key using PBKDF2
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        import base64

        # In production, derive from user passphrase with proper salt
        # For now, use the key directly if it's already 32 bytes
        if isinstance(self.encryption_key, str):
            key_bytes = self.encryption_key.encode('utf-8')
        else:
            key_bytes = self.encryption_key

        # Pad or truncate to 32 bytes
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'0')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]

        return key_bytes

    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt data using AES-256-GCM.

        Args:
            data: Plaintext string

        Returns:
            Encrypted bytes
        """
        if not self.encryption_key:
            return data.encode('utf-8')

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self._get_encryption_key()
        aesgcm = AESGCM(key)

        # Generate random nonce
        import os
        nonce = os.random(12)

        # Encrypt
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)

        # Return nonce + ciphertext
        return nonce + ciphertext

    def _decrypt_data(self, data: bytes) -> str:
        """Decrypt data using AES-256-GCM.

        Args:
            data: Encrypted bytes (nonce + ciphertext)

        Returns:
            Decrypted string
        """
        if not self.encryption_key:
            return data.decode('utf-8')

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self._get_encryption_key()
        aesgcm = AESGCM(key)

        # Extract nonce (first 12 bytes) and ciphertext
        nonce = data[:12]
        ciphertext = data[12:]

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

    def initialize_database(self) -> bool:
        """Create SQLite database and tables.

        Returns:
            True if successful
        """
        import sqlite3

        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    encrypted_data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    search_params BLOB,
                    results_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
                )
            """)

            self.conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def save_preferences(self, user_id: str, preferences: UserPreferences) -> bool:
        """Save encrypted user preferences.

        Args:
            user_id: Unique user identifier
            preferences: UserPreferences object

        Returns:
            True if saved successfully
        """
        if not self.conn:
            logger.error("Database not initialized")
            return False

        try:
            import json
            from datetime import datetime

            # Update timestamps
            preferences.user_id = user_id
            preferences.updated_at = datetime.now()
            if not preferences.created_at:
                preferences.created_at = datetime.now()

            # Serialize to JSON
            json_data = json.dumps(preferences.to_dict())

            # Encrypt
            encrypted_data = self._encrypt_data(json_data)

            # Save to database
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (user_id, encrypted_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                encrypted_data,
                preferences.created_at,
                preferences.updated_at
            ))

            self.conn.commit()
            logger.info(f"Saved preferences for user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False

    def load_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Load and decrypt user preferences.

        Args:
            user_id: User identifier

        Returns:
            UserPreferences object, or None if not found
        """
        if not self.conn:
            logger.error("Database not initialized")
            return None

        try:
            import json

            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT encrypted_data FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )

            row = cursor.fetchone()
            if not row:
                logger.warning(f"No preferences found for user: {user_id}")
                return None

            # Decrypt
            decrypted_data = self._decrypt_data(row[0])

            # Deserialize
            data = json.loads(decrypted_data)
            return UserPreferences.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
            return None

    def delete_preferences(self, user_id: str) -> bool:
        """Delete user preferences.

        Args:
            user_id: User identifier

        Returns:
            True if deleted
        """
        if not self.conn:
            return False

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
            logger.info(f"Deleted preferences for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete preferences: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.initialize_database()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.conn:
            self.conn.close()
