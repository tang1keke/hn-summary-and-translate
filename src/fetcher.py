"""RSS feed fetcher module for Hacker News."""

import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RSSFetcher:
    """Fetches and parses RSS feeds with filtering capabilities."""

    def __init__(self, feed_url: str):
        """
        Initialize RSS fetcher.

        Args:
            feed_url: URL of the RSS feed to fetch
        """
        self.feed_url = feed_url

    def fetch_feed(self,
                   max_age_hours: int = 24,
                   max_items: int = 30,
                   skip_jobs: bool = False) -> List[Dict]:
        """
        Fetch and filter RSS feed items.

        Args:
            max_age_hours: Maximum age of items to include (in hours)
            max_items: Maximum number of items to return
            skip_jobs: Whether to skip job postings (Ask HN, Show HN)

        Returns:
            List of filtered feed items
        """
        try:
            logger.info(f"Fetching RSS feed from: {self.feed_url}")
            feed = feedparser.parse(self.feed_url)

            if feed.bozo:
                logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

            # Calculate cutoff time
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            items = []
            for entry in feed.entries:
                # Parse published time
                published = self._parse_published_date(entry)
                if not published or published < cutoff_time:
                    continue

                # Skip job postings if requested
                if skip_jobs and self._is_job_posting(entry.title):
                    logger.debug(f"Skipping job posting: {entry.title}")
                    continue

                # Extract item data
                item = self._extract_item_data(entry, published)
                items.append(item)

                # Limit number of items
                if len(items) >= max_items:
                    break

            logger.info(f"Fetched {len(items)} items from feed")
            return items

        except Exception as e:
            logger.error(f"Error fetching feed: {e}")
            raise

    def _parse_published_date(self, entry) -> Optional[datetime]:
        """Parse published date from feed entry."""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
            else:
                logger.warning(f"No date found for entry: {entry.get('title', 'Unknown')}")
                return None
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            return None

    def _is_job_posting(self, title: str) -> bool:
        """Check if title indicates a job posting."""
        job_indicators = ['hiring', 'seeking', 'looking for', 'job', 'career']
        title_lower = title.lower()

        # Check for Ask HN/Show HN job-related posts
        if 'ask hn:' in title_lower or 'show hn:' in title_lower:
            for indicator in job_indicators:
                if indicator in title_lower:
                    return True

        return False

    def _extract_item_data(self, entry, published: datetime) -> Dict:
        """Extract relevant data from feed entry."""
        item = {
            'title': entry.get('title', 'No title'),
            'link': entry.get('link', ''),
            'description': entry.get('description', ''),
            'published': published,
            'guid': entry.get('id', entry.get('link', '')),
            'comments': entry.get('comments', ''),
            'author': entry.get('author', '')
        }

        # Extract HN-specific data if available
        if hasattr(entry, 'tags'):
            item['tags'] = [tag.term for tag in entry.tags]

        # Try to extract points/score if present in description
        item['score'] = self._extract_score(entry.get('description', ''))

        return item

    def _extract_score(self, description: str) -> Optional[int]:
        """Extract score/points from description if present."""
        import re
        match = re.search(r'(\d+)\s+points?', description)
        if match:
            return int(match.group(1))
        return None


def fetch_multiple_feeds(feed_urls: List[str], **kwargs) -> Dict[str, List[Dict]]:
    """
    Fetch multiple RSS feeds in parallel.

    Args:
        feed_urls: List of feed URLs to fetch
        **kwargs: Arguments to pass to fetch_feed

    Returns:
        Dictionary mapping feed URLs to their items
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_url = {
            executor.submit(RSSFetcher(url).fetch_feed, **kwargs): url
            for url in feed_urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                results[url] = []

    return results