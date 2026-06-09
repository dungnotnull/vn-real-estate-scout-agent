"""Image deduplication using perceptual hashing."""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image
import imagehash
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class ImageDeduplicator:
    """Deduplicate listing images using perceptual hashing."""

    def __init__(self, hash_size: int = 8):
        """Initialize image deduplicator.

        Args:
            hash_size: Size of hash (8 for pHash, 16 for longer hash)
        """
        self.hash_size = hash_size
        self.image_hashes = {}  # image_url -> hash
        self.hash_clusters = {}  # hash -> list of image_urls

    def compute_hash(self, image_path_or_url: str) -> Optional[imagehash.ImageHash]:
        """Compute perceptual hash for an image.

        Args:
            image_path_or_url: Local path or URL of image

        Returns:
            ImageHash object or None if failed
        """
        try:
            # Try to load from URL
            if image_path_or_url.startswith('http'):
                import requests
                from io import BytesIO

                response = requests.get(image_path_or_url, timeout=10)
                response.raise_for_status()

                image = Image.open(BytesIO(response.content))
            else:
                # Load from local path
                image = Image.open(image_path_or_url)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Compute perceptual hash
            img_hash = imagehash.phash(image, hash_size=self.hash_size)

            return img_hash

        except Exception as e:
            logger.error(f"Failed to compute hash for {image_path_or_url}: {e}")
            return None

    def compute_hashes_batch(self, image_urls: List[str]) -> Dict[str, imagehash.ImageHash]:
        """Compute hashes for multiple images.

        Args:
            image_urls: List of image URLs

        Returns:
            Dict mapping URL to hash
        """
        hashes = {}

        for url in image_urls:
            img_hash = self.compute_hash(url)
            if img_hash:
                hashes[url] = img_hash

        return hashes

    def find_duplicates(self, listing_id: str, image_urls: List[str], threshold: float = 0.95) -> List[Dict[str, Any]]:
        """Find duplicate images for a listing.

        Args:
            listing_id: Current listing ID
            image_urls: List of image URLs for this listing
            threshold: Similarity threshold (0-1)

        Returns:
            List of duplicate matches
        """
        duplicates = []

        for url in image_urls:
            img_hash = self.compute_hash(url)
            if not img_hash:
                continue

            # Check against existing hashes
            for existing_url, existing_hash in self.image_hashes.items():
                if existing_hash is None:
                    continue

                # Compute similarity
                similarity = 1 - (img_hash - existing_hash) / len(existing_hash.hash) ** 2

                if similarity >= threshold:
                    duplicates.append({
                        'listing_id': listing_id,
                        'image_url': url,
                        'duplicate_of': existing_url,
                        'similarity': similarity
                    })

            # Store hash
            self.image_hashes[url] = img_hash

        return duplicates

    def cluster_similar_images(self, image_urls: List[str], threshold: float = 0.90) -> Dict[str, List[str]]:
        """Cluster similar images across all listings.

        Args:
            image_urls: List of all image URLs
            threshold: Similarity threshold for clustering

        Returns:
            Dict mapping cluster_id to list of image URLs
        """
        from collections import defaultdict

        # Compute all hashes
        hashes = self.compute_hashes_batch(image_urls)

        # Build clusters using similarity threshold
        clusters = defaultdict(list)
        cluster_id = 0

        for url1, hash1 in hashes.items():
            if hash1 is None:
                continue

            # Find if this image belongs to existing cluster
            found_cluster = None
            for cid, cluster_urls in list(clusters.items()):
                for url2 in cluster_urls:
                    if url2 in hashes and hashes[url2] is not None:
                        similarity = 1 - (hash1 - hashes[url2]) / len(hashes[url2].hash) ** 2
                        if similarity >= threshold:
                            found_cluster = cid
                            break
                if found_cluster is not None:
                    break

            if found_cluster is not None:
                clusters[found_cluster].append(url1)
            else:
                clusters[cluster_id].append(url1)
                cluster_id += 1

        return dict(clusters)

    def detect_repost_images(self, listing_id: str, image_urls: List[str]) -> List[Dict[str, Any]]:
        """Detect if listing uses reposted images (indicates duplicate/fake).

        Args:
            listing_id: Current listing ID
            image_urls: Image URLs for this listing

        Returns:
            List of suspicious repost detections
        """
        suspicious = []

        # Check for images used in multiple listings
        image_uses = defaultdict(list)

        for url in image_urls:
            if url in self.hash_clusters:
                for cluster_id, cluster_urls in self.hash_clusters.items():
                    if url in cluster_urls:
                        image_uses[cluster_id].extend(cluster_urls)

        for cluster_id, urls in image_uses.items():
            if len(urls) > 3:  # Same image in 3+ listings
                suspicious.append({
                    'listing_id': listing_id,
                    'cluster_id': cluster_id,
                    'image_count': len(urls),
                    'reason': 'Image reused in multiple listings',
                    'suspicious': True
                })

        return suspicious

    def get_image_fingerprint(self, image_urls: List[str]) -> Optional[str]:
        """Generate unique fingerprint for a set of images.

        Args:
            image_urls: List of image URLs

        Returns:
            Fingerprint string or None
        """
        hashes = self.compute_hashes_batch(image_urls)

        if not hashes:
            return None

        # Combine hashes to create fingerprint
        hash_strings = [str(h) for h in hashes.values()]
        hash_strings.sort()

        import hashlib
        fingerprint = hashlib.md5('|'.join(hash_strings).encode()).hexdigest()[:16]

        return fingerprint

    def compare_listing_images(self, listing1_images: List[str], listing2_images: List[str]) -> float:
        """Compare image sets between two listings.

        Args:
            listing1_images: Image URLs for listing 1
            listing2_images: Image URLs for listing 2

        Returns:
            Similarity score (0-1)
        """
        hashes1 = self.compute_hashes_batch(listing1_images)
        hashes2 = self.compute_hashes_batch(listing2_images)

        if not hashes1 or not hashes2:
            return 0.0

        # Find best matches
        similarities = []

        for hash1 in hashes1.values():
            max_sim = 0.0
            for hash2 in hashes2.values():
                if hash2 is not None:
                    sim = 1 - (hash1 - hash2) / len(hash2.hash) ** 2
                    max_sim = max(max_sim, sim)
            similarities.append(max_sim)

        return np.mean(similarities) if similarities else 0.0
