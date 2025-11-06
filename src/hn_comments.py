"""Hacker News comments fetcher using HN API."""

import requests
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class HNCommentsFetcher:
    """Fetches HN comments using the official HN API."""

    HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
    HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"
    DEFAULT_TIMEOUT = 5
    MAX_RETRIES = 2

    def __init__(self, timeout: int = None):
        """
        Initialize HN comments fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.session = requests.Session()

    def extract_item_id_from_url(self, comments_url: str) -> Optional[str]:
        """
        Extract HN item ID from comments URL.

        Args:
            comments_url: HN comments URL (e.g., https://news.ycombinator.com/item?id=123456)

        Returns:
            Item ID or None if not found
        """
        import re
        match = re.search(r'id=(\d+)', comments_url)
        if match:
            return match.group(1)
        return None

    def fetch_item(self, item_id: str) -> Optional[Dict]:
        """
        Fetch HN item (story) data.

        Args:
            item_id: HN item ID

        Returns:
            Item data dictionary or None if failed
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                url = f"{self.HN_API_BASE}/item/{item_id}.json"
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                logger.warning(f"Request error for item {item_id}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(0.5 ** attempt)
                else:
                    return None

            except Exception as e:
                logger.error(f"Unexpected error fetching item {item_id}: {e}")
                return None

    def fetch_comment(self, comment_id: int) -> Optional[Dict]:
        """
        Fetch a single comment.

        Args:
            comment_id: HN comment ID

        Returns:
            Comment data or None if failed
        """
        try:
            url = f"{self.HN_API_BASE}/item/{comment_id}.json"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch comment {comment_id}: {e}")
            return None

    def fetch_top_comments(self,
                          item_id: str,
                          max_comments: int = 5,
                          max_workers: int = 3) -> List[Dict]:
        """
        Fetch top-level comments for an HN item.

        Args:
            item_id: HN item ID
            max_comments: Maximum number of top comments to fetch
            max_workers: Maximum concurrent workers for fetching comments

        Returns:
            List of comment dictionaries
        """
        # Get the item first to access comment IDs
        item = self.fetch_item(item_id)
        if not item or 'kids' not in item:
            logger.debug(f"No comments found for item {item_id}")
            return []

        comment_ids = item['kids'][:max_comments]
        comments = []

        # Fetch comments concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(self.fetch_comment, cid): cid
                for cid in comment_ids
            }

            for future in as_completed(future_to_id):
                comment_id = future_to_id[future]
                try:
                    comment_data = future.result()
                    if comment_data and not comment_data.get('deleted') and not comment_data.get('dead'):
                        comments.append({
                            'id': comment_data['id'],
                            'author': comment_data.get('by', 'unknown'),
                            'text': comment_data.get('text', ''),
                            'time': comment_data.get('time', 0)
                        })
                except Exception as e:
                    logger.error(f"Error processing comment {comment_id}: {e}")

        # Sort by time (newest first, which usually correlates with top comments)
        comments.sort(key=lambda x: x['time'], reverse=True)

        logger.debug(f"Fetched {len(comments)} comments for item {item_id}")
        return comments

    def get_hn_discussion_url(self, comments_url: str) -> Optional[str]:
        """
        Get the HN discussion URL from a comments URL.

        Args:
            comments_url: URL from RSS feed

        Returns:
            Properly formatted HN discussion URL or None
        """
        item_id = self.extract_item_id_from_url(comments_url)
        if item_id:
            return self.HN_ITEM_URL.format(item_id)
        return comments_url

    def format_comment_html(self, comment: Dict) -> str:
        """
        Format a comment as HTML.

        Args:
            comment: Comment dictionary

        Returns:
            HTML formatted comment
        """
        # Clean HTML entities in comment text
        text = comment['text']
        author = comment['author']

        # Basic formatting
        return f"""<div style="margin: 10px 0; padding: 10px; background: #f6f6f6; border-left: 3px solid #ff6600;">
<p style="margin: 0 0 5px 0;"><strong>{author}:</strong></p>
<p style="margin: 0;">{text}</p>
</div>"""


def batch_fetch_comments(comments_urls: List[str],
                         max_comments_per_item: int = 5,
                         max_workers: int = 3) -> Dict[str, List[Dict]]:
    """
    Fetch comments for multiple HN items concurrently.

    Args:
        comments_urls: List of HN comments URLs
        max_comments_per_item: Maximum number of comments to fetch per item
        max_workers: Maximum concurrent workers

    Returns:
        Dictionary mapping URLs to their comments
    """
    fetcher = HNCommentsFetcher()
    results = {}

    # Extract item IDs
    url_to_id = {}
    for url in comments_urls:
        item_id = fetcher.extract_item_id_from_url(url)
        if item_id:
            url_to_id[url] = item_id

    # Fetch comments for each item
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(fetcher.fetch_top_comments, item_id, max_comments_per_item): url
            for url, item_id in url_to_id.items()
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                comments = future.result()
                results[url] = comments
                if comments:
                    logger.info(f"Fetched {len(comments)} comments for {url[:50]}...")
                else:
                    logger.debug(f"No comments for {url[:50]}...")
            except Exception as e:
                logger.error(f"Error fetching comments for {url}: {e}")
                results[url] = []

    return results
