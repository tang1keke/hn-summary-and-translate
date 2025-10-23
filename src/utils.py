"""Utility functions and cache management."""

import json
import logging
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pickle

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of processed items."""

    def __init__(self, cache_dir: str = 'cache', ttl_days: int = 7):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files
            ttl_days: Time to live for cached items in days
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_days = ttl_days
        self.cache_file = self.cache_dir / 'processed_items.json'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from disk with TTL enforcement."""
        if not self.cache_file.exists():
            logger.debug("No cache file found, starting with empty cache")
            return {}

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Clean expired entries
            cutoff_time = datetime.now() - timedelta(days=self.ttl_days)
            cutoff_str = cutoff_time.isoformat()

            cleaned_cache = {}
            expired_count = 0

            for key, value in cache_data.items():
                if isinstance(value, dict):
                    processed_at = value.get('processed_at', '')
                    if processed_at > cutoff_str:
                        cleaned_cache[key] = value
                    else:
                        expired_count += 1

            if expired_count > 0:
                logger.info(f"Removed {expired_count} expired cache entries")

            return cleaned_cache

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return {}

    def save_cache(self):
        """Save cache to disk."""
        try:
            # Add timestamp to all entries
            for key in self.cache:
                if isinstance(self.cache[key], dict) and 'processed_at' not in self.cache[key]:
                    self.cache[key]['processed_at'] = datetime.now().isoformat()

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, default=str)

            logger.debug(f"Saved cache with {len(self.cache)} entries")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, key: str) -> Optional[Dict]:
        """Get cached item by key."""
        return self.cache.get(key)

    def set(self, key: str, value: Dict):
        """Set cache item."""
        if not isinstance(value, dict):
            value = {'data': value}
        value['processed_at'] = datetime.now().isoformat()
        self.cache[key] = value

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache

    def clear_old(self):
        """Clear entries older than TTL."""
        cutoff_time = datetime.now() - timedelta(days=self.ttl_days)
        cutoff_str = cutoff_time.isoformat()

        keys_to_remove = []
        for key, value in self.cache.items():
            if isinstance(value, dict):
                processed_at = value.get('processed_at', '')
                if processed_at < cutoff_str:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            logger.info(f"Cleared {len(keys_to_remove)} old cache entries")


class ModelCache:
    """Cache for ML model outputs to avoid re-processing."""

    def __init__(self, cache_dir: str = 'cache'):
        """Initialize model cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.summary_cache_file = self.cache_dir / 'summaries.pkl'
        self.translation_cache_file = self.cache_dir / 'translations.pkl'

    def get_content_hash(self, content: str) -> str:
        """Generate hash for content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_summary(self, content: str) -> Optional[str]:
        """Get cached summary if available."""
        if not self.summary_cache_file.exists():
            return None

        try:
            with open(self.summary_cache_file, 'rb') as f:
                cache = pickle.load(f)
                content_hash = self.get_content_hash(content)
                return cache.get(content_hash)
        except Exception:
            return None

    def set_summary(self, content: str, summary: str):
        """Cache a summary."""
        try:
            cache = {}
            if self.summary_cache_file.exists():
                with open(self.summary_cache_file, 'rb') as f:
                    cache = pickle.load(f)

            content_hash = self.get_content_hash(content)
            cache[content_hash] = summary

            with open(self.summary_cache_file, 'wb') as f:
                pickle.dump(cache, f)
        except Exception as e:
            logger.error(f"Failed to cache summary: {e}")

    def get_translation(self, text: str, target_lang: str) -> Optional[str]:
        """Get cached translation if available."""
        if not self.translation_cache_file.exists():
            return None

        try:
            with open(self.translation_cache_file, 'rb') as f:
                cache = pickle.load(f)
                key = f"{target_lang}_{self.get_content_hash(text)}"
                return cache.get(key)
        except Exception:
            return None

    def set_translation(self, text: str, target_lang: str, translation: str):
        """Cache a translation."""
        try:
            cache = {}
            if self.translation_cache_file.exists():
                with open(self.translation_cache_file, 'rb') as f:
                    cache = pickle.load(f)

            key = f"{target_lang}_{self.get_content_hash(text)}"
            cache[key] = translation

            with open(self.translation_cache_file, 'wb') as f:
                pickle.dump(cache, f)
        except Exception as e:
            logger.error(f"Failed to cache translation: {e}")


def setup_logging(level: str = 'INFO'):
    """
    Set up logging configuration.

    Args:
        level: Logging level
    """
    log_format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def deduplicate_items(new_items: List[Dict], cache: Dict) -> List[Dict]:
    """
    Remove duplicate items based on URL.

    Args:
        new_items: List of new items to check
        cache: Dictionary of cached items

    Returns:
        List of unique new items
    """
    unique_items = []
    seen_urls = set()

    # Extract URLs from cache
    for cached_item in cache.values():
        if isinstance(cached_item, dict):
            url = cached_item.get('link') or cached_item.get('url')
            if url:
                seen_urls.add(url)

    # Filter new items
    for item in new_items:
        url = item.get('link')
        if url and url not in seen_urls:
            unique_items.append(item)
            seen_urls.add(url)

    logger.debug(f"Deduplicated: {len(new_items)} -> {len(unique_items)} unique items")
    return unique_items


def get_url_hash(url: str) -> str:
    """Generate a hash for a URL."""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def load_config(config_path: str = 'config.yaml') -> Dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    import yaml

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.debug(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


def ensure_directories(*paths):
    """Ensure directories exist."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def clean_text_for_processing(text: str, max_length: int = 5000) -> str:
    """
    Clean and truncate text for processing.

    Args:
        text: Raw text
        max_length: Maximum length

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = ' '.join(text.split())

    # Truncate if necessary
    if len(text) > max_length:
        text = text[:max_length]
        # Try to cut at sentence boundary
        last_period = text.rfind('.')
        if last_period > max_length * 0.8:
            text = text[:last_period + 1]

    return text


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        import time
        now = time.time()
        time_since_last = now - self.last_call
        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)
        self.last_call = time.time()


def format_item_for_display(item: Dict, lang: str = 'en') -> str:
    """
    Format an item for display in logs or debug output.

    Args:
        item: Item dictionary
        lang: Language code

    Returns:
        Formatted string
    """
    title = item.get('title', 'No title')[:50]
    url = item.get('link', 'No URL')[:50]
    return f"[{lang}] {title}... ({url}...)"


def calculate_processing_stats(start_time: datetime,
                              items_processed: int,
                              items_failed: int) -> Dict:
    """
    Calculate processing statistics.

    Args:
        start_time: Processing start time
        items_processed: Number of successfully processed items
        items_failed: Number of failed items

    Returns:
        Statistics dictionary
    """
    duration = (datetime.now() - start_time).total_seconds()
    total_items = items_processed + items_failed

    stats = {
        'duration_seconds': duration,
        'items_processed': items_processed,
        'items_failed': items_failed,
        'total_items': total_items,
        'success_rate': (items_processed / total_items * 100) if total_items > 0 else 0,
        'items_per_second': total_items / duration if duration > 0 else 0
    }

    return stats


def print_processing_summary(stats: Dict):
    """Print processing summary."""
    print("\n" + "=" * 50)
    print("Processing Summary")
    print("=" * 50)
    print(f"Duration: {stats['duration_seconds']:.1f} seconds")
    print(f"Items processed: {stats['items_processed']}")
    print(f"Items failed: {stats['items_failed']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Processing speed: {stats['items_per_second']:.2f} items/second")
    print("=" * 50)