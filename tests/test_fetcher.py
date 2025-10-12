"""Tests for RSS fetcher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from src.fetcher import RSSFetcher, fetch_multiple_feeds


class TestRSSFetcher:
    """Test cases for RSSFetcher class."""

    @pytest.fixture
    def mock_feed_data(self):
        """Create mock feed data."""
        now = datetime.now()
        return Mock(
            bozo=False,
            entries=[
                Mock(
                    title="Test Article 1",
                    link="https://example.com/1",
                    description="Description 1",
                    id="item-1",
                    comments="https://news.ycombinator.com/item?id=1",
                    author="author1",
                    published_parsed=now.timetuple()[:9],
                    tags=[]
                ),
                Mock(
                    title="Test Article 2",
                    link="https://example.com/2",
                    description="Description 2 with 42 points",
                    id="item-2",
                    comments="https://news.ycombinator.com/item?id=2",
                    author="author2",
                    published_parsed=(now - timedelta(hours=1)).timetuple()[:9],
                    tags=[]
                ),
                Mock(
                    title="Ask HN: Looking for job opportunities",
                    link="https://example.com/3",
                    description="Job posting",
                    id="item-3",
                    comments="https://news.ycombinator.com/item?id=3",
                    author="author3",
                    published_parsed=(now - timedelta(hours=2)).timetuple()[:9],
                    tags=[]
                )
            ]
        )

    def test_fetch_feed_success(self, mock_feed_data):
        """Test successful feed fetching."""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value = mock_feed_data

            fetcher = RSSFetcher("https://test.com/rss")
            items = fetcher.fetch_feed(max_age_hours=24, max_items=10)

            assert len(items) == 3
            assert items[0]['title'] == "Test Article 1"
            assert items[0]['link'] == "https://example.com/1"
            assert items[0]['guid'] == "item-1"

    def test_fetch_feed_with_age_filter(self, mock_feed_data):
        """Test feed fetching with age filtering."""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value = mock_feed_data

            fetcher = RSSFetcher("https://test.com/rss")
            items = fetcher.fetch_feed(max_age_hours=1.5, max_items=10)

            # Should only get items from last 1.5 hours
            assert len(items) == 2
            assert "Test Article 1" in [item['title'] for item in items]
            assert "Test Article 2" in [item['title'] for item in items]

    def test_fetch_feed_with_job_filter(self, mock_feed_data):
        """Test feed fetching with job posting filter."""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value = mock_feed_data

            fetcher = RSSFetcher("https://test.com/rss")
            items = fetcher.fetch_feed(skip_jobs=True)

            # Should filter out job posting
            assert len(items) == 2
            assert all("job" not in item['title'].lower() for item in items)

    def test_fetch_feed_max_items(self, mock_feed_data):
        """Test feed fetching with max items limit."""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value = mock_feed_data

            fetcher = RSSFetcher("https://test.com/rss")
            items = fetcher.fetch_feed(max_items=1)

            assert len(items) == 1
            assert items[0]['title'] == "Test Article 1"

    def test_extract_score(self, mock_feed_data):
        """Test score extraction from description."""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value = mock_feed_data

            fetcher = RSSFetcher("https://test.com/rss")
            items = fetcher.fetch_feed()

            # Second item has "42 points" in description
            item_with_score = next(i for i in items if i['title'] == "Test Article 2")
            assert item_with_score['score'] == 42

    def test_fetch_feed_error_handling(self):
        """Test error handling in feed fetching."""
        with patch('feedparser.parse') as mock_parse:
            mock_parse.side_effect = Exception("Network error")

            fetcher = RSSFetcher("https://test.com/rss")
            with pytest.raises(Exception):
                fetcher.fetch_feed()


class TestFetchMultipleFeeds:
    """Test cases for fetch_multiple_feeds function."""

    def test_fetch_multiple_success(self):
        """Test fetching multiple feeds successfully."""
        with patch('src.fetcher.RSSFetcher') as MockFetcher:
            mock_instance = MockFetcher.return_value
            mock_instance.fetch_feed.return_value = [
                {'title': 'Item 1', 'link': 'https://example.com/1'}
            ]

            urls = ["https://feed1.com", "https://feed2.com"]
            results = fetch_multiple_feeds(urls)

            assert len(results) == 2
            assert all(url in results for url in urls)

    def test_fetch_multiple_partial_failure(self):
        """Test fetching multiple feeds with partial failure."""
        with patch('src.fetcher.RSSFetcher') as MockFetcher:
            mock_instance = MockFetcher.return_value

            def side_effect(*args, **kwargs):
                if MockFetcher.call_count == 1:
                    return [{'title': 'Item 1'}]
                else:
                    raise Exception("Feed error")

            mock_instance.fetch_feed.side_effect = side_effect

            urls = ["https://feed1.com", "https://feed2.com"]
            with patch('src.fetcher.logger'):
                results = fetch_multiple_feeds(urls)

            # Should still return results for successful feeds
            assert len(results) == 2
            # Failed feed should have empty list
            assert any(len(items) == 0 for items in results.values())